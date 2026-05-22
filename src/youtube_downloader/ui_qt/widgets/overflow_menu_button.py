"""Toolbar overflow menu (⋯) for secondary row actions."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMenu, QToolButton, QWidget

from PySide6.QtCore import Qt


class OverflowMenuButton(QToolButton):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tooltip: str = "Mais ações",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("overflowMenu")
        self.setToolTip(tooltip)
        self.setText("⋯")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def set_actions(
        self,
        actions: list[tuple[str, Callable[[], None], bool]],
    ) -> None:
        """Each entry: (label, callback, enabled)."""
        menu = QMenu(self)
        for label, callback, enabled in actions:
            action = menu.addAction(label)
            action.setEnabled(enabled)
            action.triggered.connect(callback)
        self.setMenu(menu)
