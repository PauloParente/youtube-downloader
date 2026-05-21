"""Sidebar navigation button with animated hover and press."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from youtube_downloader.ui_qt.theme import polish_widget
from youtube_downloader.ui_qt.theme_tokens import (
    NAV_ANIM_HOVER_IN_MS,
    NAV_ANIM_HOVER_OUT_MS,
)


class NavButton(QPushButton):
    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        *,
        focusable: bool = True,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("nav")
        self.setFlat(True)
        self.setCheckable(False)
        self.setAutoFillBackground(False)
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus if focusable else Qt.FocusPolicy.NoFocus
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._is_nav_active = False
        self._hover_t = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.valueChanged.connect(self._on_hover_changed)

    def set_nav_active(self, active: bool) -> None:
        self._is_nav_active = active
        self.setProperty("navActive", "true" if active else "false")
        polish_widget(self)
        if active:
            self._hover_t = 0.0
            self._hover_anim.stop()
        row = self.parent()
        if row is not None:
            row.update()

    def is_nav_active(self) -> bool:
        return self._is_nav_active

    def _on_hover_changed(self, value) -> None:
        self._hover_t = float(value)
        row = self.parent()
        if row is not None:
            row.update()

    def _animate_hover(self, end: float, duration: int, curve: QEasingCurve.Type) -> None:
        self._hover_anim.stop()
        self._hover_anim.setDuration(duration)
        self._hover_anim.setStartValue(self._hover_t)
        self._hover_anim.setEndValue(end)
        self._hover_anim.setEasingCurve(curve)
        self._hover_anim.start()

    def enterEvent(self, event) -> None:  # noqa: N802
        if not self._is_nav_active:
            self._animate_hover(1.0, NAV_ANIM_HOVER_IN_MS, QEasingCurve.Type.OutCubic)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._animate_hover(0.0, NAV_ANIM_HOVER_OUT_MS, QEasingCurve.Type.InCubic)
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        row = self.parent()
        if row is not None:
            row.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        row = self.parent()
        if row is not None:
            row.update()
