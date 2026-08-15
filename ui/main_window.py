"""Top-level window: persistent status bar + QStackedWidget of screens.

Owns navigation and wires backend signals to the status bar, connection
overlay, and whichever screens care about them. Screens themselves never
touch the backend directly -- they call back through MainWindow's
`backend` reference (still the PrinterBackend interface, never a concrete
class) and receive state via apply_state()/PrinterState.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from config import Config, save_config
from printer.base import PrinterBackend
from state import ConnectionState, GcodeState, PrinterState
from ui.status_bar import StatusBar
from ui.widgets.connection_overlay import ConnectionOverlay
from ui.widgets.hms_banner import HMSBanner
from ui.widgets.loading_overlay import LoadingOverlay
from ui.widgets.toast import Toast


class MainWindow(QMainWindow):
    def __init__(self, backend: PrinterBackend, config: Config) -> None:
        super().__init__()
        self.backend = backend
        self.config = config
        self.setObjectName("mainWindow")
        self.setWindowTitle("P1S Touch Control")

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.status_bar_widget = StatusBar()
        self.status_bar_widget.quit_requested.connect(self._on_quit_requested)
        outer.addWidget(self.status_bar_widget)

        self.hms_banner = HMSBanner()
        outer.addWidget(self.hms_banner)

        self.toast = Toast()
        outer.addWidget(self.toast)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        self._screens: dict[str, QWidget] = {}
        self._current_screen_name: str | None = None
        self._was_printing = False
        self._cursor_hidden = False

        self._overlay = ConnectionOverlay(central)
        self.loading_overlay = LoadingOverlay(central)

        self._build_screens()

        self.backend.state_changed.connect(self._on_state_changed)
        self.backend.connection_changed.connect(self._on_connection_changed)
        self.backend.error.connect(self._on_error)
        self.backend.print_start_warning.connect(self._on_print_start_warning)

    def _build_screens(self) -> None:
        # imported here (not at module top) to avoid a circular import: the
        # screen modules import MainWindow only for type hints.
        from ui.screens.control import ControlScreen
        from ui.screens.filament_ams import FilamentAMSScreen
        from ui.screens.first_run import FirstRunScreen
        from ui.screens.home import HomeScreen
        from ui.screens.print_files import PrintFilesScreen
        from ui.screens.print_monitor import PrintMonitorScreen
        from ui.screens.settings import SettingsScreen

        self.register_screen("home", HomeScreen(self))
        self.register_screen("print_files", PrintFilesScreen(self))
        self.register_screen("print_monitor", PrintMonitorScreen(self))
        self.register_screen("filament_ams", FilamentAMSScreen(self))
        self.register_screen("control", ControlScreen(self))
        self.register_screen("settings", SettingsScreen(self))
        self.register_screen("first_run", FirstRunScreen(self))

        start_screen = "first_run" if not self.config.is_ready else "home"
        self.navigate_to(start_screen)

    def apply_window_mode(self, fullscreen: bool) -> None:
        """Show fullscreen or windowed without touching config.

        Used both for the initial launch (where main.py's --windowed flag
        is a temporary dev override, not a saved preference) and
        internally by set_fullscreen().
        """
        app = QApplication.instance()
        if fullscreen:
            self.showFullScreen()
            if not self._cursor_hidden:
                app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
                self._cursor_hidden = True
        else:
            if self._cursor_hidden:
                app.restoreOverrideCursor()
                self._cursor_hidden = False
            self.showNormal()

    def set_fullscreen(self, fullscreen: bool) -> None:
        """User-facing toggle (Settings screen) -- persists the choice."""
        self.config.app.fullscreen = fullscreen
        save_config(self.config)
        self.apply_window_mode(fullscreen)

    def register_screen(self, name: str, widget: QWidget) -> None:
        self._screens[name] = widget
        self.stack.addWidget(widget)

    def navigate_to(self, name: str) -> None:
        widget = self._screens.get(name)
        if widget is None:
            return
        self._current_screen_name = name
        self.stack.setCurrentWidget(widget)
        on_shown = getattr(widget, "on_shown", None)
        if callable(on_shown):
            on_shown()
        self._update_overlay_visibility()

    # -- backend signal handlers -------------------------------------------
    def _on_state_changed(self, state: PrinterState) -> None:
        self.status_bar_widget.apply_state(state)
        self.hms_banner.apply_errors(state.hms_errors)
        for widget in self._screens.values():
            apply_state = getattr(widget, "apply_state", None)
            if callable(apply_state):
                apply_state(state)

        is_printing_now = state.gcode_state in (GcodeState.RUNNING, GcodeState.PAUSE)
        if is_printing_now and not self._was_printing and self._current_screen_name == "home":
            self.navigate_to("print_monitor")
        self._was_printing = is_printing_now

    def _on_connection_changed(self, connection: ConnectionState) -> None:
        self._update_overlay_visibility(connection)

    def _on_error(self, message: str) -> None:
        self.toast.show_message(message)

    def _on_print_start_warning(self, message: str) -> None:
        # The print hasn't actually started yet at this point (see
        # RealBackend._on_print_start_resolved) -- this is a real decision,
        # not just an FYI, so Cancel is the default/focused button rather
        # than "Print Anyway": a wrong-material print is wasted filament
        # and time at best, so an accidental Enter-press shouldn't be the
        # one that commits to it.
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("AMS Filament Mismatch")
        box.setText(message)
        print_anyway = box.addButton("Print Anyway", QMessageBox.ButtonRole.AcceptRole)
        cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        if box.clickedButton() is print_anyway:
            self.backend.confirm_pending_print()
        else:
            self.backend.cancel_pending_print()

    def _on_quit_requested(self) -> None:
        reply = QMessageBox.question(self, "Quit", "Quit the application?")
        if reply == QMessageBox.StandardButton.Yes:
            self.close()

    def _update_overlay_visibility(self, connection: ConnectionState | None = None) -> None:
        connection = connection if connection is not None else self.backend.state.connection
        # Settings/first-run must stay usable even while disconnected --
        # that's exactly where the user fixes connection details.
        if self._current_screen_name in ("settings", "first_run"):
            self._overlay.hide()
            return
        self._overlay.apply_state(connection)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._overlay.setGeometry(self.centralWidget().rect())
        self.loading_overlay.setGeometry(self.centralWidget().rect())
