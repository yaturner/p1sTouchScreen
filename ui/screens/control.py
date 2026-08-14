from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QVBoxLayout, QWidget,
)

from state import PrinterState
from ui.widgets.keypad import NumericKeypadDialog

_STEP_SIZES = [0.1, 1, 10]


class ControlScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("controlScreen")
        self._step_mm = 1

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        back_btn = QPushButton("← Home")
        back_btn.clicked.connect(lambda: main_window.navigate_to("home"))
        header.addWidget(back_btn)
        header.addWidget(QLabel("Control"), 1)
        root.addLayout(header)

        body = QHBoxLayout()
        body.addLayout(self._build_jog_pad())
        body.addLayout(self._build_temps_and_fans())
        root.addLayout(body, 1)

    # -- jog pad -----------------------------------------------------
    def _build_jog_pad(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel("Move"))

        grid = QGridLayout()
        y_plus = QPushButton("Y+")
        y_plus.clicked.connect(lambda: self._jog("Y", self._step_mm))
        grid.addWidget(y_plus, 0, 1)

        x_minus = QPushButton("X-")
        x_minus.clicked.connect(lambda: self._jog("X", -self._step_mm))
        grid.addWidget(x_minus, 1, 0)

        home_btn = QPushButton("⌂")
        home_btn.clicked.connect(lambda: self._main_window.backend.home_axes())
        grid.addWidget(home_btn, 1, 1)

        x_plus = QPushButton("X+")
        x_plus.clicked.connect(lambda: self._jog("X", self._step_mm))
        grid.addWidget(x_plus, 1, 2)

        y_minus = QPushButton("Y-")
        y_minus.clicked.connect(lambda: self._jog("Y", -self._step_mm))
        grid.addWidget(y_minus, 2, 1)

        z_plus = QPushButton("Z+")
        z_plus.clicked.connect(lambda: self._jog("Z", self._step_mm))
        grid.addWidget(z_plus, 0, 3)

        z_minus = QPushButton("Z-")
        z_minus.clicked.connect(lambda: self._jog("Z", -self._step_mm))
        grid.addWidget(z_minus, 2, 3)

        col.addLayout(grid)

        step_row = QHBoxLayout()
        step_group = QButtonGroup(self)
        for size in _STEP_SIZES:
            radio = QRadioButton(f"{size} mm")
            radio.setChecked(size == self._step_mm)
            radio.toggled.connect(lambda checked, s=size: self._set_step(s) if checked else None)
            step_group.addButton(radio)
            step_row.addWidget(radio)
        col.addLayout(step_row)

        extrude_row = QHBoxLayout()
        extrude_btn = QPushButton("Extrude")
        extrude_btn.clicked.connect(self._on_extrude)
        extrude_row.addWidget(extrude_btn)
        retract_btn = QPushButton("Retract")
        retract_btn.clicked.connect(self._on_retract)
        extrude_row.addWidget(retract_btn)
        col.addLayout(extrude_row)

        col.addStretch(1)
        return col

    def _set_step(self, size: float) -> None:
        self._step_mm = size

    def _jog(self, axis: str, distance_mm: float) -> None:
        self._main_window.backend.jog(axis, distance_mm)

    def _on_extrude(self) -> None:
        dialog = NumericKeypadDialog("Extrude", unit_label="mm", initial_value=10,
                                       min_val=0, max_val=200)
        if dialog.exec() and dialog.value:
            self._main_window.backend.extrude(dialog.value)

    def _on_retract(self) -> None:
        dialog = NumericKeypadDialog("Retract", unit_label="mm", initial_value=10,
                                       min_val=0, max_val=200)
        if dialog.exec() and dialog.value:
            self._main_window.backend.extrude(-dialog.value)

    # -- temps / fans / light --------------------------------------------
    def _build_temps_and_fans(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel("Temperature"))

        self._nozzle_btn = QPushButton("Nozzle: -- / --°C")
        self._nozzle_btn.clicked.connect(self._on_set_nozzle)
        col.addWidget(self._nozzle_btn)

        self._bed_btn = QPushButton("Bed: -- / --°C")
        self._bed_btn.clicked.connect(self._on_set_bed)
        col.addWidget(self._bed_btn)

        col.addWidget(QLabel("Fans"))
        fan_row = QHBoxLayout()
        self._fan_buttons: dict[str, QPushButton] = {}
        for fan_key, label in (("part", "Part"), ("aux", "Aux"), ("chamber", "Chamber")):
            btn = QPushButton(f"{label}: --%")
            btn.clicked.connect(lambda checked=False, k=fan_key, n=label: self._on_set_fan(k, n))
            fan_row.addWidget(btn)
            self._fan_buttons[fan_key] = btn
        col.addLayout(fan_row)

        self._light_btn = QPushButton("Light: --")
        self._light_btn.clicked.connect(self._on_toggle_light)
        col.addWidget(self._light_btn)

        col.addStretch(1)
        return col

    def _on_set_nozzle(self) -> None:
        current = self._main_window.backend.state.nozzle_target or 0
        dialog = NumericKeypadDialog("Nozzle Target", unit_label="°C", initial_value=current,
                                       min_val=0, max_val=300)
        if dialog.exec() and dialog.value is not None:
            self._main_window.backend.set_nozzle_target(int(dialog.value))

    def _on_set_bed(self) -> None:
        current = self._main_window.backend.state.bed_target or 0
        dialog = NumericKeypadDialog("Bed Target", unit_label="°C", initial_value=current,
                                       min_val=0, max_val=120)
        if dialog.exec() and dialog.value is not None:
            self._main_window.backend.set_bed_target(int(dialog.value))

    def _on_set_fan(self, fan_key: str, label: str) -> None:
        current = self._main_window.backend.state.fan_speeds.get(fan_key, 0)
        dialog = NumericKeypadDialog(f"{label} Fan", unit_label="%", initial_value=current,
                                       min_val=0, max_val=100)
        if dialog.exec() and dialog.value is not None:
            self._main_window.backend.set_fan_speed(fan_key, int(dialog.value))

    def _on_toggle_light(self) -> None:
        backend = self._main_window.backend
        if backend.state.light_on:
            backend.light_off()
        else:
            backend.light_on()

    def apply_state(self, state: PrinterState) -> None:
        n_cur = _fmt(state.nozzle_temp)
        n_tgt = _fmt(state.nozzle_target)
        self._nozzle_btn.setText(f"Nozzle: {n_cur} / {n_tgt}°C")

        b_cur = _fmt(state.bed_temp)
        b_tgt = _fmt(state.bed_target)
        self._bed_btn.setText(f"Bed: {b_cur} / {b_tgt}°C")

        for fan_key, btn in self._fan_buttons.items():
            label = {"part": "Part", "aux": "Aux", "chamber": "Chamber"}[fan_key]
            pct = state.fan_speeds.get(fan_key, 0)
            btn.setText(f"{label}: {pct}%")

        if state.light_on is not None:
            self._light_btn.setText(f"Light: {'On' if state.light_on else 'Off'}")


def _fmt(value) -> str:
    if value is None:
        return "--"
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"
