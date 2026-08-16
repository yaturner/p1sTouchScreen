"""Single AMS tray/slot widget used on the Filament screen."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from state import AMSTray


class AMSSlotWidget(QFrame):
    load_requested = Signal(int)
    unload_requested = Signal(int)
    edit_requested = Signal(int)

    def __init__(self, slot_index: int, parent=None) -> None:
        super().__init__(parent)
        self.slot_index = slot_index
        self.setObjectName("amsSlot")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.tray = AMSTray(slot_index=slot_index)

        root = QVBoxLayout(self)

        self._swatch = QLabel()
        self._swatch.setObjectName("amsSwatch")
        self._swatch.setFixedHeight(28)
        root.addWidget(self._swatch)

        self._type_label = QLabel(f"Slot {slot_index + 1}")
        self._type_label.setObjectName("amsTypeLabel")
        self._type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._type_label)

        btn_row = QHBoxLayout()
        self._load_btn = QPushButton("Load")
        self._load_btn.clicked.connect(lambda: self.load_requested.emit(self.slot_index))
        btn_row.addWidget(self._load_btn)

        self._unload_btn = QPushButton("Unload")
        self._unload_btn.clicked.connect(lambda: self.unload_requested.emit(self.slot_index))
        btn_row.addWidget(self._unload_btn)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.slot_index))
        btn_row.addWidget(self._edit_btn)
        root.addLayout(btn_row)

        self.set_tray(AMSTray(slot_index=slot_index))

    def set_tray(self, tray: AMSTray, busy: bool = False) -> None:
        self.tray = tray
        color = tray.color_hex or "#3a3a3a"
        self._swatch.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        if tray.is_empty:
            self._type_label.setText(f"Slot {self.slot_index + 1}: Empty")
        else:
            active = " • active" if tray.is_active else ""
            # Prefer the RFID's specific product name (e.g. "PLA
            # Translucent") over the generic material category ("PLA")
            # when the printer reports one.
            name = tray.sub_brand or tray.filament_type or "?"
            self._type_label.setText(f"Slot {self.slot_index + 1}: {name}{active}")
        self.setProperty("active", tray.is_active)
        self.style().unpolish(self)
        self.style().polish(self)
        # Disabled while any load/unload is in flight -- firing a second
        # one mid-swap is untested territory. Load/Unload are also disabled
        # on an empty slot -- nothing to feed in or retract. Edit stays
        # enabled on an empty slot, though: it pre-labels a slot's filament
        # type/color before a spool is physically inserted, same as the
        # printer's own Edit-slot screen allows.
        enabled = not busy
        self._load_btn.setEnabled(enabled and not tray.is_empty)
        self._unload_btn.setEnabled(enabled and not tray.is_empty)
        self._edit_btn.setEnabled(enabled)
