"""Auto-hiding one-off message for backend command/connection errors.

Separate from HMSBanner on purpose: that banner reflects the printer's
own ongoing HMS condition (state to keep showing until it clears or is
dismissed), while a command failure or a dropped connection is an event
("your last tap didn't go through") that shouldn't stick around. Reusing
HMSBanner's label for both used to mean a transient error could be
clobbered within about a second by the next state poll's apply_errors()
call -- confirmed live as a real defect, not just a theoretical one.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QWidget

_DISPLAY_MS = 4000


class Toast(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setWordWrap(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        self.hide()

    def show_message(self, message: str) -> None:
        self.setText(message)
        self.show()
        self._timer.start(_DISPLAY_MS)
