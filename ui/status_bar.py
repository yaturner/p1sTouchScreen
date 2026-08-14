"""Top status bar: nozzle/bed temp, connection state, camera indicator -- mirrors the
small icon row along the top of the real A1 screen."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from state import ConnectionState, PrinterState

_CONNECTION_ICONS = {
    ConnectionState.CONNECTED: "🟢",
    ConnectionState.CONNECTING: "🟡",
    ConnectionState.RECONNECTING: "🟡",
    ConnectionState.DISCONNECTED: "🔴",
}


class StatusBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        self._nozzle_label = QLabel("Nozzle: -- / --°C")
        self._nozzle_label.setObjectName("statusNozzle")
        layout.addWidget(self._nozzle_label)

        self._bed_label = QLabel("Bed: -- / --°C")
        self._bed_label.setObjectName("statusBed")
        layout.addWidget(self._bed_label)

        layout.addStretch(1)

        self._camera_label = QLabel("📷")
        self._camera_label.setObjectName("statusCamera")
        layout.addWidget(self._camera_label)

        self._connection_label = QLabel("🔴")
        self._connection_label.setObjectName("statusConnection")
        layout.addWidget(self._connection_label)

    def apply_state(self, state: PrinterState) -> None:
        nozzle_cur = _fmt(state.nozzle_temp)
        nozzle_tgt = _fmt(state.nozzle_target)
        self._nozzle_label.setText(f"Nozzle: {nozzle_cur} / {nozzle_tgt}°C")

        bed_cur = _fmt(state.bed_temp)
        bed_tgt = _fmt(state.bed_target)
        self._bed_label.setText(f"Bed: {bed_cur} / {bed_tgt}°C")

        self._connection_label.setText(_CONNECTION_ICONS.get(state.connection, "🔴"))
        self._camera_label.setVisible(state.connection == ConnectionState.CONNECTED)


def _fmt(value) -> str:
    if value is None:
        return "--"
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"
