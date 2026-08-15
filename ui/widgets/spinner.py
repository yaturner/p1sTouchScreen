"""Small rotating dot-ring spinner for indicating background loading."""
from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

_DOT_COUNT = 12
_ACCENT = QColor("#00b371")


class Spinner(QWidget):
    def __init__(self, diameter: int = 64, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self._head = 0
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._advance)

    def start(self) -> None:
        self._head = 0
        self._timer.start()
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _advance(self) -> None:
        self._head = (self._head + 1) % _DOT_COUNT
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        cx, cy = self.width() / 2, self.height() / 2
        radius = min(cx, cy) - 6
        dot_radius = radius * 0.16
        for i in range(_DOT_COUNT):
            angle = 2 * math.pi * i / _DOT_COUNT - math.pi / 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            trail = (self._head - i) % _DOT_COUNT
            opacity = max(0.12, 1.0 - trail / _DOT_COUNT)
            color = QColor(_ACCENT)
            color.setAlphaF(opacity)
            painter.setBrush(color)
            painter.drawEllipse(QRectF(x - dot_radius, y - dot_radius, dot_radius * 2, dot_radius * 2))
        painter.end()
