from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from state import GcodeState, PrinterState
from ui.widgets.nav_tile import NavTile


class HomeScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("homeScreen")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        self._banner = QPushButton()
        self._banner.setObjectName("printBanner")
        self._banner.clicked.connect(lambda: self._main_window.navigate_to("print_monitor"))
        self._banner.hide()
        root.addWidget(self._banner)

        grid = QGridLayout()
        grid.setSpacing(16)
        tiles = [
            ("🗂", "Print Files", "print_files"),
            ("🧵", "Filament", "filament_ams"),
            ("🎛", "Control", "control"),
            ("⚙", "Settings", "settings"),
            ("🩺", "Assistant", "settings"),  # calibration wizards are future work; parks on Settings for now
        ]
        columns = 3
        for i, (icon, label, target) in enumerate(tiles):
            tile = NavTile(icon, label)
            tile.clicked.connect(lambda t=target: self._main_window.navigate_to(t))
            grid.addWidget(tile, i // columns, i % columns)
        rows = -(-len(tiles) // columns)  # ceil division
        for r in range(rows):
            grid.setRowStretch(r, 1)
        for c in range(columns):
            grid.setColumnStretch(c, 1)
        root.addLayout(grid, 1)

    def apply_state(self, state: PrinterState) -> None:
        if state.gcode_state in (GcodeState.RUNNING, GcodeState.PAUSE):
            pct = state.print_percent if state.print_percent is not None else 0
            name = state.current_file or "print job"
            status = "Paused" if state.gcode_state == GcodeState.PAUSE else "Printing"
            self._banner.setText(f"{status}: {name} — {pct}%  (tap to view)")
            self._banner.show()
        else:
            self._banner.hide()
