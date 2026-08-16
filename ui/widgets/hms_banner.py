"""Slim banner showing the printer's current HMS error(s), if any.

Unlike ConnectionOverlay this doesn't block the rest of the screen --
an HMS warning (e.g. "AMS is drying") doesn't necessarily mean the user
can't still use Control/Settings/etc, so it sits as a dismissible strip
rather than a full-screen block.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class HMSBanner(QWidget):
    # Navigates to the Assistant screen's full list of active HMS errors --
    # the banner only ever shows the first one (see apply_errors), so this
    # is the way to actually see every currently-active fault's full text.
    check_solution_requested = Signal()

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

        solution_btn = QPushButton("Check Solution")
        solution_btn.setObjectName("hmsBannerSolution")
        solution_btn.clicked.connect(self._on_check_solution)
        layout.addWidget(solution_btn)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setObjectName("hmsBannerDismiss")
        dismiss_btn.clicked.connect(self._on_dismiss)
        layout.addWidget(dismiss_btn)

        self._dismissed_messages: set[str] = set()
        self.hide()

    def apply_errors(self, messages: list[str]) -> None:
        if not messages:
            # The printer itself has no active HMS entries at all -- reset
            # dismissals so a genuine NEW occurrence of a fault that was
            # dismissed earlier (even one with the identical message,
            # since these are keyed by text, not a timestamp/instance id)
            # shows again rather than staying silently suppressed for the
            # rest of the session. HMS entries can be safety-relevant on a
            # 3D printer -- "you dismissed a similar alert an hour ago" is
            # not a good enough reason to hide a fresh one.
            self._dismissed_messages.clear()
            self.hide()
            return
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

    def _on_check_solution(self) -> None:
        # Same "acknowledged, stop showing it" effect as Dismiss -- Check
        # Solution is a stronger acknowledgement than a plain dismiss (the
        # user is actively going to go read about it), not a weaker one.
        self._on_dismiss()
        self.check_solution_requested.emit()
