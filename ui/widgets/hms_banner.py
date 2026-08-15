"""Slim banner showing the printer's current HMS error(s), if any.

Unlike ConnectionOverlay this doesn't block the rest of the screen --
an HMS warning (e.g. "AMS is drying") doesn't necessarily mean the user
can't still use Control/Settings/etc, so it sits as a dismissible strip
rather than a full-screen block.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class HMSBanner(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("hmsBanner")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        self._label = QLabel("")
        self._label.setObjectName("hmsBannerLabel")
        self._label.setWordWrap(True)
        layout.addWidget(self._label, 1)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setObjectName("hmsBannerDismiss")
        dismiss_btn.clicked.connect(self._on_dismiss)
        layout.addWidget(dismiss_btn)

        self._dismissed_messages: set[str] = set()
        self.hide()

    def apply_errors(self, messages: list[str]) -> None:
        active = [m for m in messages if m not in self._dismissed_messages]
        if not active:
            self.hide()
            return
        # Multiple simultaneous HMS entries are rare; showing the first
        # (most severe/most recent as reported by the printer) keeps this
        # readable on a small touch panel instead of stacking banners.
        self._label.setText(active[0])
        self.show()

    def _on_dismiss(self) -> None:
        self._dismissed_messages.add(self._label.text())
        self.hide()

    def show_transient(self, message: str) -> None:
        """Show a one-off backend error (not tied to ongoing HMS state)."""
        self._label.setText(message)
        self.show()
