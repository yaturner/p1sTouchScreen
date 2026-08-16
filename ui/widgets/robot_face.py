"""Hand-drawn happy/sad robot face for the Assistant tile.

Unicode has no matching happy/sad-with-X-eyes robot emoji pair (unlike
every other Home tile, which just uses a plain emoji glyph), so this is
drawn with QPainter instead.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap


def draw_robot_face(sad: bool, size: int) -> QPixmap:
    color = "#e53935" if sad else "#43a047"
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(size * 0.06)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    head_top = size * 0.22
    head_left = size * 0.08
    head_w = size * 0.84
    head_h = size * 0.72

    # Antenna
    painter.drawLine(QPointF(size * 0.5, head_top), QPointF(size * 0.5, 0))
    painter.setBrush(QColor(color))
    painter.drawEllipse(QPointF(size * 0.5, size * 0.04), size * 0.05, size * 0.05)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # Head
    painter.drawRoundedRect(QRectF(head_left, head_top, head_w, head_h), size * 0.15, size * 0.15)

    eye_y = head_top + head_h * 0.38
    left_eye_x = head_left + head_w * 0.3
    right_eye_x = head_left + head_w * 0.7
    eye_r = size * 0.07

    # QPainter.drawArc: 0deg = 3 o'clock, POSITIVE angles sweep
    # counter-clockwise (90deg = 12 o'clock/top, 270deg = 6 o'clock/bottom)
    # -- opposite rotation direction from Compose's drawArc. A smile bulges
    # downward (passes through the bottom point, 270deg); a frown bulges
    # upward (passes through the top point, 90deg).
    mouth_rect = QRectF(
        head_left + head_w * 0.22, head_top + head_h * 0.5,
        head_w * 0.56, head_h * 0.34,
    )
    if sad:
        # X eyes
        for cx in (left_eye_x, right_eye_x):
            painter.drawLine(QPointF(cx - eye_r, eye_y - eye_r), QPointF(cx + eye_r, eye_y + eye_r))
            painter.drawLine(QPointF(cx - eye_r, eye_y + eye_r), QPointF(cx + eye_r, eye_y - eye_r))
        # Frown mouth (top arc, bulges upward)
        painter.drawArc(mouth_rect, 20 * 16, 140 * 16)
    else:
        # Dot eyes
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPointF(left_eye_x, eye_y), eye_r * 0.7, eye_r * 0.7)
        painter.drawEllipse(QPointF(right_eye_x, eye_y), eye_r * 0.7, eye_r * 0.7)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Smile mouth (bottom arc, bulges downward)
        painter.drawArc(mouth_rect, 200 * 16, 140 * 16)

    painter.end()
    return pixmap
