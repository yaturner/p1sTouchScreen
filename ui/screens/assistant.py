"""Assistant screen: full list of the printer's currently-active HMS errors.

Reached via the HMS banner's "Check Solution" button (or the Home tile) --
the banner itself only ever shows the first active error (see
HMSBanner.apply_errors), so this is the way to actually see every
currently-active fault's full text at once.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget

from state import PrinterState


class AssistantScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("assistantScreen")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        back_btn = QPushButton("← Home")
        back_btn.clicked.connect(lambda: main_window.navigate_to("home"))
        header.addWidget(back_btn)
        header.addWidget(QLabel("Assistant"), 1)
        # Full auto-calibration (bed leveling + vibration compensation +
        # motor noise cancellation) -- a real, multi-minute operation that
        # physically moves the extruder and print bed, so this needs the
        # same confirm-before-acting treatment as Stop Print, not a bare
        # button.
        calibrate_btn = QPushButton("Run Calibration")
        calibrate_btn.clicked.connect(self._on_run_calibration)
        header.addWidget(calibrate_btn)
        root.addLayout(header)

        self._list = QListWidget()
        self._list.setObjectName("assistantHmsList")
        self._list.setWordWrap(True)
        root.addWidget(self._list, 1)

    def _on_run_calibration(self) -> None:
        reply = QMessageBox.question(
            self, "Run Calibration",
            "Run full calibration (bed leveling, vibration compensation, motor "
            "noise cancellation)? This takes several minutes and moves the "
            "extruder and print bed -- make sure the bed is clear.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._main_window.backend.run_calibration()

    def apply_state(self, state: PrinterState) -> None:
        self._list.clear()
        if not state.hms_errors:
            self._list.addItem("No active HMS errors.")
            return
        self._list.addItems(state.hms_errors)
