"""Assistant screen: full list of the printer's currently-active HMS errors.

Reached via the HMS banner's "Check Solution" button (or the Home tile) --
the banner itself only ever shows the first active error (see
HMSBanner.apply_errors), so this is the way to actually see every
currently-active fault's full text at once.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

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
        root.addLayout(header)

        self._list = QListWidget()
        self._list.setObjectName("assistantHmsList")
        self._list.setWordWrap(True)
        root.addWidget(self._list, 1)

    def apply_state(self, state: PrinterState) -> None:
        self._list.clear()
        if not state.hms_errors:
            self._list.addItem("No active HMS errors.")
            return
        self._list.addItems(state.hms_errors)
