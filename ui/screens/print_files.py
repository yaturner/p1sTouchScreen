from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from state import PrintFile


class PrintFilesScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("printFilesScreen")
        self._files: list[PrintFile] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        back_btn = QPushButton("← Home")
        back_btn.clicked.connect(lambda: main_window.navigate_to("home"))
        header.addWidget(back_btn)
        header.addWidget(QLabel("Print Files"), 1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        self._list = QListWidget()
        self._list.itemActivated.connect(self._on_item_activated)
        root.addWidget(self._list, 1)

        self._main_window.backend.file_list_ready.connect(self._on_files_ready)

    def on_shown(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        self._list.addItem("Loading…")
        self._main_window.backend.request_file_list()

    def _on_files_ready(self, files: list[PrintFile]) -> None:
        self._files = files
        self._list.clear()
        if not files:
            self._list.addItem("No files found on printer.")
            return
        for f in files:
            size = f" ({f.size_bytes // 1024} KB)" if f.size_bytes else ""
            item = QListWidgetItem(f"{f.name}{size}")
            self._list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        index = self._list.row(item)
        if index < 0 or index >= len(self._files):
            return
        chosen = self._files[index]
        reply = QMessageBox.question(
            self, "Start Print", f"Print '{chosen.name}'?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._main_window.backend.start_print(chosen.path)
            self._main_window.navigate_to("print_monitor")
