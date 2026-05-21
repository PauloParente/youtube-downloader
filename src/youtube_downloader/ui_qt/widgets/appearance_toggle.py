"""Single discreet button to switch dark / light appearance."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from youtube_downloader.ui_qt.theme_tokens import NAV_ITEM_HEIGHT

from youtube_downloader.core.appearance import dark_enabled_for_mode
from youtube_downloader.ui_qt.icons import icon_on_button


class AppearanceToggle(QPushButton):
    """Icon shows the mode to activate on click (sun → light, moon → dark)."""

    _ICON_SIZE = 16

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_mode_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("appearanceToggle")
        self._on_mode_changed = on_mode_changed
        self._mode = "dark"
        self._syncing = False
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(NAV_ITEM_HEIGHT, NAV_ITEM_HEIGHT)
        self.setIconSize(QSize(self._ICON_SIZE, self._ICON_SIZE))
        self.clicked.connect(self._on_clicked)
        self.set_mode("dark")

    def _icon_for_active_mode(self, mode: str) -> str:
        return "sun" if dark_enabled_for_mode(mode) else "moon"

    def _tooltip_for_active_mode(self, mode: str) -> str:
        return "Modo claro" if dark_enabled_for_mode(mode) else "Modo escuro"

    def _on_clicked(self) -> None:
        if self._syncing:
            return
        new_mode = "light" if dark_enabled_for_mode(self._mode) else "dark"
        if self._on_mode_changed is not None:
            self._on_mode_changed(new_mode)

    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._syncing = True
        try:
            self._mode = "light" if mode == "light" else "dark"
            icon_on_button(self, self._icon_for_active_mode(self._mode), size=self._ICON_SIZE)
            self.setToolTip(self._tooltip_for_active_mode(self._mode))
        finally:
            self._syncing = False

    def refresh_icons(self) -> None:
        icon_on_button(self, self._icon_for_active_mode(self._mode), size=self._ICON_SIZE)
