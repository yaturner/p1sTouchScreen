"""Reusable large touch-friendly home-screen navigation button."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


class NavTile(QWidget):
    clicked = Signal()

    def __init__(self, icon_text: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navTile")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._button = QPushButton(self)
        self._button.setObjectName("navTileButton")
        self._button.clicked.connect(self.clicked.emit)
        self._button.setMinimumSize(150, 150)
        self._button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button)

        inner = QVBoxLayout(self._button)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon = QLabel(icon_text)
        self._icon.setObjectName("navTileIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(self._icon)

        text = QLabel(label)
        text.setObjectName("navTileLabel")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(text)

    def set_icon_pixmap(self, pixmap: QPixmap) -> None:
        # Swaps the emoji-glyph icon for a drawn one -- used by the
        # Assistant tile's dynamic happy/sad robot face, which Unicode has
        # no matching emoji pair for.
        self._icon.setPixmap(pixmap)
