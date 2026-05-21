"""Styled push buttons."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QWidget


class PrimaryButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("primary")


class GhostButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("ghost")


class DangerButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("danger")


class LinkButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("link")
        self.setFlat(True)


class IconButton(QPushButton):
    def __init__(
        self,
        icon: QIcon | None = None,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("iconOnly")
        if icon is not None:
            self.setIcon(icon)
        self.setIconSize(QSize(18, 18))
        if tooltip:
            self.setToolTip(tooltip)
