"""Translucent full-window overlay shown while disconnected/reconnecting."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from state import ConnectionState

_MESSAGES = {
    ConnectionState.DISCONNECTED: "Not connected",
    ConnectionState.CONNECTING: "Connecting to printer…",
    ConnectionState.RECONNECTING: "Connection lost — retrying…",
}


class ConnectionOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("connectionOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("")
        self._label.setObjectName("connectionOverlayLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self.hide()

    def apply_state(self, connection: ConnectionState) -> None:
        message = _MESSAGES.get(connection)
        if message is None:
            self.hide()
            return
        self._label.setText(message)
        self.show()
        self.raise_()

    def resizeEventToParent(self) -> None:
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
