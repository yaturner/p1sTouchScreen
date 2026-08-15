"""Full-window translucent overlay showing a centered spinner during blocking loads."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.widgets.spinner import Spinner


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = Spinner(72)
        layout.addWidget(self._spinner)

        self.hide()

    def show_loading(self) -> None:
        self._spinner.start()
        self.show()
        self.raise_()

    def hide_loading(self) -> None:
        self._spinner.stop()
        self.hide()
