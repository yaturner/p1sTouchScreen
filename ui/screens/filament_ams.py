from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from state import PrinterState
from ui.widgets.ams_slot import AMSSlotWidget


class FilamentAMSScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("filamentAmsScreen")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        back_btn = QPushButton("← Home")
        back_btn.clicked.connect(lambda: main_window.navigate_to("home"))
        header.addWidget(back_btn)
        header.addWidget(QLabel("Filament / AMS"), 1)
        # Re-requests the printer's current state immediately -- there's no
        # local command that forces the AMS to re-scan a spool's RFID tag,
        # so this just skips the wait for the next periodic refresh (e.g.
        # right after swapping a spool).
        sync_btn = QPushButton("Sync")
        sync_btn.clicked.connect(self._on_sync)
        header.addWidget(sync_btn)
        root.addLayout(header)

        slots_row = QHBoxLayout()
        self._slots: list[AMSSlotWidget] = []
        for i in range(4):
            slot = AMSSlotWidget(i)
            slot.load_requested.connect(self._on_load)
            slot.unload_requested.connect(self._on_unload)
            slots_row.addWidget(slot)
            self._slots.append(slot)
        root.addLayout(slots_row)
        root.addStretch(1)

    def _on_sync(self) -> None:
        # sync_ams() fires a real MQTT command but is otherwise silent --
        # confirmed live that it published every time, but with no visible
        # effect (AMS data is usually already fresh from the periodic
        # refresh), tapping it felt broken. This toast is the only
        # feedback the user gets that anything happened.
        self._main_window.backend.sync_ams()
        self._main_window.toast.show_message("AMS synced")

    def _on_load(self, slot_index: int) -> None:
        self._main_window.backend.load_filament(slot_index)

    def _on_unload(self, slot_index: int) -> None:
        self._main_window.backend.unload_filament(slot_index)

    def apply_state(self, state: PrinterState) -> None:
        by_index = {t.slot_index: t for t in state.ams_trays}
        for i, widget in enumerate(self._slots):
            tray = by_index.get(i)
            if tray is not None:
                widget.set_tray(tray)
