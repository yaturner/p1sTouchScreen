from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from state import GcodeState, PrinterState

_SPEED_LEVELS = {"Silent": 1, "Standard": 2, "Sport": 3, "Ludicrous": 4}


class PrintMonitorScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("printMonitorScreen")
        self._suppress_speed_signal = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        back_btn = QPushButton("← Home")
        back_btn.clicked.connect(lambda: main_window.navigate_to("home"))
        header.addWidget(back_btn)
        self._state_label = QLabel("Idle")
        self._state_label.setObjectName("printState")
        header.addWidget(self._state_label, 1)
        root.addLayout(header)

        self._camera_label = QLabel("No camera feed")
        self._camera_label.setObjectName("cameraFeed")
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setMinimumHeight(240)
        root.addWidget(self._camera_label, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        root.addWidget(self._progress)

        info_row = QHBoxLayout()
        self._layer_label = QLabel("Layer: -- / --")
        info_row.addWidget(self._layer_label)
        self._eta_label = QLabel("ETA: --")
        info_row.addWidget(self._eta_label)
        root.addLayout(info_row)

        controls = QHBoxLayout()
        self._pause_btn = QPushButton("Pause")
        self._pause_btn.clicked.connect(self._on_pause_resume)
        controls.addWidget(self._pause_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("dangerButton")
        self._stop_btn.clicked.connect(self._on_stop)
        controls.addWidget(self._stop_btn)

        self._speed_combo = QComboBox()
        self._speed_combo.addItems(list(_SPEED_LEVELS.keys()))
        self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
        controls.addWidget(self._speed_combo)
        root.addLayout(controls)

        self._main_window.backend.camera_frame.connect(self._on_camera_frame)

    def _on_pause_resume(self) -> None:
        backend = self._main_window.backend
        if backend.state.gcode_state == GcodeState.PAUSE:
            backend.resume_print()
        else:
            backend.pause_print()

    def _on_stop(self) -> None:
        self._main_window.backend.stop_print()

    def _on_speed_changed(self, text: str) -> None:
        if self._suppress_speed_signal:
            return
        level = _SPEED_LEVELS.get(text)
        if level is not None:
            self._main_window.backend.set_speed_level(level)

    def _on_camera_frame(self, image) -> None:
        pixmap = QPixmap.fromImage(image)
        self._camera_label.setPixmap(
            pixmap.scaled(self._camera_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        )

    def apply_state(self, state: PrinterState) -> None:
        self._state_label.setText(state.gcode_state.name.title())
        self._progress.setValue(state.print_percent or 0)
        layer_cur = state.current_layer if state.current_layer is not None else "--"
        layer_tot = state.total_layer if state.total_layer is not None else "--"
        self._layer_label.setText(f"Layer: {layer_cur} / {layer_tot}")
        eta = f"{state.remaining_minutes} min" if state.remaining_minutes is not None else "--"
        self._eta_label.setText(f"ETA: {eta}")
        self._pause_btn.setText("Resume" if state.gcode_state == GcodeState.PAUSE else "Pause")

        if state.speed_level is not None:
            for label, level in _SPEED_LEVELS.items():
                if level == state.speed_level:
                    self._suppress_speed_signal = True
                    self._speed_combo.setCurrentText(label)
                    self._suppress_speed_signal = False
                    break
