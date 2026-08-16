"""Modal dialog for editing an AMS slot's stored filament type + color.

Mirrors the printer's own "Edit slot" screen (Filament/Color), minus
"Dynamic pressure control" -- there's no local MQTT command to set a
manual K/N pressure-advance override (checked bambulabs_api's full
command set), only the full auto-calibration sequence, so it's left out
rather than guessed at.
"""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from filament_presets import MANUFACTURERS, PRESETS_BY_MANUFACTURER, preset_key
from state import AMSTray


class AmsEditDialog(QDialog):
    """Modal filament editor. Use exec() and read .filament_key/.color_hex
    after acceptance."""

    def __init__(self, slot_index: int, tray: AMSTray, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setObjectName("amsEditDialog")
        self.setWindowTitle(f"Edit Slot {slot_index + 1}")
        self.filament_key: str | None = None
        self.color_hex: str | None = None
        self._color = QColor(tray.color_hex or "#FFFFFF")

        root = QVBoxLayout(self)
        root.setSpacing(12)

        root.addWidget(QLabel("Manufacturer"))
        self._manufacturer_combo = QComboBox()
        self._manufacturer_combo.addItems(MANUFACTURERS)
        # The printer's telemetry only reports material type (e.g. "PLA"),
        # never which brand a loaded spool is, so there's nothing to guess
        # from -- always starts on Bambu Lab.
        self._manufacturer_combo.currentTextChanged.connect(self._on_manufacturer_changed)
        root.addWidget(self._manufacturer_combo)

        root.addWidget(QLabel("Filament"))
        self._type_combo = QComboBox()
        root.addWidget(self._type_combo)
        self._populate_types(MANUFACTURERS[0], initial_type=tray.filament_type)

        root.addWidget(QLabel("Color"))
        self._color_btn = QPushButton()
        self._color_btn.setMinimumHeight(48)
        self._color_btn.clicked.connect(self._pick_color)
        self._update_color_button()
        root.addWidget(self._color_btn)

        actions = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._confirm)
        actions.addWidget(ok_btn)
        root.addLayout(actions)

    def _on_manufacturer_changed(self, manufacturer: str) -> None:
        self._populate_types(manufacturer)

    def _populate_types(self, manufacturer: str, initial_type: str | None = None) -> None:
        self._type_combo.clear()
        presets = PRESETS_BY_MANUFACTURER.get(manufacturer, [])
        self._type_combo.addItems([p.label for p in presets])
        if initial_type:
            # Best-effort: land on a preset whose material matches the
            # tray's reported type (e.g. "PLA"), not necessarily its exact
            # sub-variant (Matte/Silk/etc, which telemetry doesn't report).
            match = next((p.label for p in presets if p.tray_type == initial_type), None)
            if match:
                self._type_combo.setCurrentText(match)

    def _pick_color(self) -> None:
        chosen = QColorDialog.getColor(self._color, self, "Filament Color")
        if chosen.isValid():
            self._color = chosen
            self._update_color_button()

    def _update_color_button(self) -> None:
        self._color_btn.setStyleSheet(f"background-color: {self._color.name()};")
        self._color_btn.setText(self._color.name().upper())

    def _confirm(self) -> None:
        manufacturer = self._manufacturer_combo.currentText()
        type_label = self._type_combo.currentText()
        if not type_label:
            return
        self.filament_key = preset_key(manufacturer, type_label)
        self.color_hex = self._color.name().upper()
        self.accept()
