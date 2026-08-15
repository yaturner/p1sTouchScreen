from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

import bambulabs_api
from state import PrinterState

_APP_VERSION = "0.1.0"


class SettingsScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("settingsScreen")
        self._code_revealed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        back_btn = QPushButton("← Home")
        back_btn.clicked.connect(lambda: main_window.navigate_to("home"))
        header.addWidget(back_btn)
        header.addWidget(QLabel("Settings"), 1)
        root.addLayout(header)

        cfg = main_window.config.printer
        root.addWidget(QLabel(f"Printer IP: {cfg.ip or '(not set)'}"))
        root.addWidget(QLabel(f"Serial: {cfg.serial or '(not set)'}"))

        self._code_label = QLabel(self._masked_code())
        self._code_label.mousePressEvent = lambda _e: self._toggle_code()
        root.addWidget(self._code_label)

        self._connection_label = QLabel("Connection: unknown")
        root.addWidget(self._connection_label)

        reconnect_btn = QPushButton("Reconnect")
        reconnect_btn.clicked.connect(self._on_reconnect)
        root.addWidget(reconnect_btn)

        display_row = QHBoxLayout()
        display_row.addWidget(QLabel("Display mode:"))
        self._fullscreen_btn = QPushButton()
        self._fullscreen_btn.clicked.connect(self._on_toggle_fullscreen)
        display_row.addWidget(self._fullscreen_btn)
        display_row.addStretch(1)
        root.addLayout(display_row)
        self._update_fullscreen_button()

        root.addWidget(QLabel(""))
        root.addWidget(QLabel(f"App version: {_APP_VERSION}"))
        root.addWidget(QLabel(f"bambulabs_api version: {getattr(bambulabs_api, '__version__', 'unknown')}"))
        root.addWidget(QLabel(f"Backend: {main_window.config.app.backend}"))

        root.addStretch(1)

        power_row = QHBoxLayout()
        restart_btn = QPushButton("Restart App")
        restart_btn.clicked.connect(self._on_restart_app)
        power_row.addWidget(restart_btn)

        exit_btn = QPushButton("Exit App")
        exit_btn.setObjectName("dangerButton")
        exit_btn.clicked.connect(self._on_exit_app)
        power_row.addWidget(exit_btn)

        shutdown_btn = QPushButton("Shutdown Pi")
        shutdown_btn.setObjectName("dangerButton")
        shutdown_btn.clicked.connect(self._on_shutdown_pi)
        power_row.addWidget(shutdown_btn)
        root.addLayout(power_row)

    def _masked_code(self) -> str:
        code = self._main_window.config.printer.access_code
        if not code:
            return "Access code: (not set)"
        shown = code if self._code_revealed else "•" * len(code)
        return f"Access code: {shown}  (tap to {'hide' if self._code_revealed else 'reveal'})"

    def _toggle_code(self) -> None:
        self._code_revealed = not self._code_revealed
        self._code_label.setText(self._masked_code())

    def _on_reconnect(self) -> None:
        backend = self._main_window.backend
        backend.disconnect_printer()
        backend.connect_printer()

    def _update_fullscreen_button(self) -> None:
        is_fullscreen = self._main_window.config.app.fullscreen
        self._fullscreen_btn.setText("Switch to Windowed" if is_fullscreen else "Switch to Fullscreen")

    def _on_toggle_fullscreen(self) -> None:
        self._main_window.set_fullscreen(not self._main_window.config.app.fullscreen)
        self._update_fullscreen_button()

    def _on_restart_app(self) -> None:
        reply = QMessageBox.question(self, "Restart App", "Restart the application now?")
        if reply == QMessageBox.StandardButton.Yes:
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def _on_exit_app(self) -> None:
        reply = QMessageBox.question(self, "Exit App", "Quit the application?")
        if reply == QMessageBox.StandardButton.Yes:
            self._main_window.close()

    def _on_shutdown_pi(self) -> None:
        reply = QMessageBox.question(self, "Shutdown Pi", "Shut down the Raspberry Pi now?")
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)

    def apply_state(self, state: PrinterState) -> None:
        self._connection_label.setText(f"Connection: {state.connection.name.title()}")
