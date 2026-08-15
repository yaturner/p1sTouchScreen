from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from state import PrintFile

_ICON_SIZE = 128

_SORT_KEYS = {
    "Name": lambda f: f.name.lower(),
    "Date": lambda f: f.modified or datetime.min,
    "Size": lambda f: f.size_bytes or 0,
}


def _build_placeholder_icon(size: int) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#23272e"))
    painter.setPen(QColor("#3a3f47"))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 10, 10)
    font = painter.font()
    font.setPointSize(int(size * 0.4))
    painter.setFont(font)
    painter.setPen(QColor("#6b7280"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "📄")
    painter.end()
    return QIcon(pixmap)


class PrintFilesScreen(QWidget):
    def __init__(self, main_window) -> None:
        super().__init__()
        self._main_window = main_window
        self.setObjectName("printFilesScreen")
        self._files: list[PrintFile] = []
        self._items_by_path: dict[str, QListWidgetItem] = {}
        self._thumbnails: dict[str, QPixmap] = {}
        self._sort_field = "Name"
        self._sort_desc = False
        self._search_text = ""
        self._placeholder_icon = _build_placeholder_icon(_ICON_SIZE)

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

        toolbar = QHBoxLayout()
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search files…")
        self._search_box.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self._search_box, 1)

        toolbar.addWidget(QLabel("Sort:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(list(_SORT_KEYS))
        self._sort_combo.currentTextChanged.connect(self._on_sort_field_changed)
        toolbar.addWidget(self._sort_combo)

        self._sort_dir_btn = QPushButton("↑")
        self._sort_dir_btn.setFixedWidth(44)
        self._sort_dir_btn.clicked.connect(self._on_sort_dir_toggled)
        toolbar.addWidget(self._sort_dir_btn)
        root.addLayout(toolbar)
        self._toolbar_widgets = [self._search_box, self._sort_combo, self._sort_dir_btn]

        self._loading_bar = QProgressBar()
        self._loading_bar.setObjectName("filesLoadingBar")
        self._loading_bar.setRange(0, 0)  # indeterminate
        self._loading_bar.setTextVisible(False)
        self._loading_bar.setFixedHeight(6)
        self._loading_bar.hide()
        root.addWidget(self._loading_bar)

        self._list = QListWidget()
        self._list.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self._list.itemActivated.connect(self._on_item_activated)
        root.addWidget(self._list, 1)

        self._main_window.backend.file_list_ready.connect(self._on_files_ready)
        self._main_window.backend.thumbnail_ready.connect(self._on_thumbnail_ready)

    def on_shown(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._files = []
        self._thumbnails.clear()
        self._list.clear()
        self._items_by_path.clear()
        self._list.hide()
        self._loading_bar.show()
        for w in self._toolbar_widgets:
            w.setEnabled(False)
        self._main_window.backend.request_file_list()

    def _on_files_ready(self, files: list[PrintFile]) -> None:
        self._files = files
        self._thumbnails.clear()
        self._loading_bar.hide()
        self._list.show()
        for w in self._toolbar_widgets:
            w.setEnabled(True)
        self._render_list()

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text
        self._render_list()

    def _on_sort_field_changed(self, field: str) -> None:
        self._sort_field = field
        self._render_list()

    def _on_sort_dir_toggled(self) -> None:
        self._sort_desc = not self._sort_desc
        self._sort_dir_btn.setText("↓" if self._sort_desc else "↑")
        self._render_list()

    def _visible_files(self) -> list[PrintFile]:
        files = self._files
        if self._search_text:
            needle = self._search_text.lower()
            files = [f for f in files if needle in f.name.lower()]
        key_fn = _SORT_KEYS[self._sort_field]
        return sorted(files, key=key_fn, reverse=self._sort_desc)

    def _render_list(self) -> None:
        self._list.clear()
        self._items_by_path.clear()
        if not self._files:
            self._list.addItem("No files found on printer.")
            return
        visible = self._visible_files()
        if not visible:
            self._list.addItem("No files match your search.")
            return
        for f in visible:
            size = f" ({f.size_bytes // 1024} KB)" if f.size_bytes else ""
            item = QListWidgetItem(f"{f.name}{size}")
            item.setData(Qt.ItemDataRole.UserRole, f.path)
            cached = self._thumbnails.get(f.path)
            item.setIcon(QIcon(cached) if cached is not None else self._placeholder_icon)
            self._list.addItem(item)
            self._items_by_path[f.path] = item

    def _on_thumbnail_ready(self, path: str, image) -> None:
        pixmap = QPixmap.fromImage(image).scaled(
            _ICON_SIZE, _ICON_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )
        self._thumbnails[path] = pixmap
        item = self._items_by_path.get(path)
        if item is not None:
            item.setIcon(QIcon(pixmap))

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        chosen = next((f for f in self._files if f.path == path), None)
        if chosen is None:
            return
        reply = QMessageBox.question(
            self, "Start Print", f"Print '{chosen.name}'?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._main_window.backend.start_print(chosen.path)
            self._main_window.navigate_to("print_monitor")
