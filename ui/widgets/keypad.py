"""Reusable on-screen numeric entry -- there's no physical keyboard attached."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

_BUTTON_SIZE = 64


class NumericKeypadDialog(QDialog):
    """Modal numeric keypad. Use exec() and read .value after acceptance."""

    def __init__(
        self,
        title: str,
        unit_label: str = "",
        initial_value: float = 0,
        min_val: float = 0,
        max_val: float = 300,
        allow_decimal: bool = False,
        allow_negative: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setObjectName("keypadDialog")
        self.setWindowTitle(title)
        self._min = min_val
        self._max = max_val
        self._allow_decimal = allow_decimal
        self._allow_negative = allow_negative
        self._entry = "" if initial_value == 0 else _format_initial(initial_value)
        self.value: float | None = None

        root = QVBoxLayout(self)
        root.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("keypadTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title_label)

        self._display = QLabel()
        self._display.setObjectName("keypadDisplay")
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setMinimumHeight(56)
        root.addWidget(self._display)

        grid = QGridLayout()
        grid.setSpacing(8)
        buttons = ["7", "8", "9", "4", "5", "6", "1", "2", "3"]
        positions = [(r, c) for r in range(3) for c in range(3)]
        for (r, c), label in zip(positions, buttons):
            grid.addWidget(self._make_digit_button(label), r, c)

        if allow_negative:
            grid.addWidget(self._make_digit_button("-"), 3, 0)
        else:
            grid.addWidget(self._make_spacer(), 3, 0)

        grid.addWidget(self._make_digit_button("0"), 3, 1)

        if allow_decimal:
            grid.addWidget(self._make_digit_button("."), 3, 2)
        else:
            grid.addWidget(self._make_spacer(), 3, 2)

        backspace = QPushButton("⌫")
        backspace.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        backspace.setObjectName("keypadBackspace")
        backspace.clicked.connect(self._backspace)
        grid.addWidget(backspace, 0, 3)
        root.addLayout(grid)

        actions = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("keypadCancel")
        cancel_btn.setMinimumHeight(56)
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.setObjectName("keypadConfirm")
        confirm_btn.setMinimumHeight(56)
        confirm_btn.clicked.connect(self._confirm)
        actions.addWidget(confirm_btn)
        root.addLayout(actions)

        self._refresh_display(unit_label)
        self._unit_label = unit_label

    def _make_digit_button(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        btn.setObjectName("keypadDigit")
        btn.clicked.connect(lambda: self._append(label))
        return btn

    def _make_spacer(self) -> QWidget:
        w = QWidget()
        w.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        return w

    def _append(self, char: str) -> None:
        if char == "." and "." in self._entry:
            return
        if char == "-" and self._entry:
            return  # only allow leading minus
        self._entry += char
        self._refresh_display(self._unit_label)

    def _backspace(self) -> None:
        self._entry = self._entry[:-1]
        self._refresh_display(self._unit_label)

    def _refresh_display(self, unit_label: str) -> None:
        text = self._entry if self._entry else "0"
        self._display.setText(f"{text} {unit_label}".strip())

    def _confirm(self) -> None:
        try:
            value = float(self._entry) if self._entry not in ("", "-") else 0.0
        except ValueError:
            value = 0.0
        value = max(self._min, min(self._max, value))
        self.value = value
        self.accept()


def _format_initial(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)
