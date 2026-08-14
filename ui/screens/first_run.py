"""First-run setup: collect printer IP/serial/access code and write config.yaml.

Uses plain QLineEdits rather than a custom on-screen QWERTY keyboard --
this is a one-time setup step, and building a full alphanumeric keyboard
widget is out of scope (see config.example.yaml's comment on where to find
these values). On a bare kiosk image with no physical keyboard attached,
install a system virtual keyboard (e.g. squeekboard on labwc/Wayland, or
matchbox-keyboard on X11) so QLineEdit gets an input panel; that's an OS
concern, not something this app needs to reimplement. Editing config.yaml
directly over SSH is the other supported path -- see deploy notes.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from config import save_config


class FirstRunScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("firstRunScreen")

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.addWidget(QLabel("Printer Setup"))
        root.addWidget(QLabel(
            "Enter your P1S's LAN details (Bambu Studio/Handy → printer → "
            "Settings → enable 'LAN Only Mode')."
        ))

        form = QFormLayout()
        self._ip_edit = QLineEdit(main_window.config.printer.ip)
        form.addRow("IP address", self._ip_edit)
        self._serial_edit = QLineEdit(main_window.config.printer.serial)
        form.addRow("Serial number", self._serial_edit)
        self._code_edit = QLineEdit(main_window.config.printer.access_code)
        self._code_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Access code", self._code_edit)
        root.addLayout(form)

        save_btn = QPushButton("Save & Continue")
        save_btn.clicked.connect(self._on_save)
        root.addWidget(save_btn)

        skip_btn = QPushButton("Skip (use mock/demo mode)")
        skip_btn.clicked.connect(self._on_skip)
        root.addWidget(skip_btn)

        root.addStretch(1)

    def _on_save(self) -> None:
        cfg = self._main_window.config
        cfg.printer.ip = self._ip_edit.text().strip()
        cfg.printer.serial = self._serial_edit.text().strip()
        cfg.printer.access_code = self._code_edit.text().strip()
        if not cfg.printer.is_complete:
            QMessageBox.warning(self, "Incomplete", "All three fields are required.")
            return
        cfg.app.backend = "real"
        save_config(cfg)
        QMessageBox.information(
            self, "Saved",
            "Settings saved. Restart the app to connect to your printer.",
        )
        self._main_window.navigate_to("settings")

    def _on_skip(self) -> None:
        self._main_window.navigate_to("home")
