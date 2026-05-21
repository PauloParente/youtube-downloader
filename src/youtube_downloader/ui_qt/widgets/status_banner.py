"""Dismissible status banner for transient messages."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from youtube_downloader.ui_qt.icons import accent_icon
from youtube_downloader.ui_qt.widgets.buttons import IconButton


_BANNER_SLOT_NAME = "statusBannerSlot"


class StatusBanner(QFrame):
    def __init__(
        self,
        parent=None,
        *,
        on_dismiss: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statusBanner")
        self.hide()
        self._on_dismiss = on_dismiss

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        self._message = QLabel()
        self._message.setWordWrap(True)
        self._message.setAutoFillBackground(False)
        layout.addWidget(self._message, stretch=1)
        close = IconButton(tooltip="Fechar")
        close.setObjectName("statusBannerClose")
        close.setAutoFillBackground(False)
        close.setIcon(accent_icon("clear", 14))
        close.setIconSize(QSize(14, 14))
        close.clicked.connect(self._dismiss)
        layout.addWidget(close)

    def _set_slot_visible(self, visible: bool) -> None:
        slot = self.parentWidget()
        if slot is not None and slot.objectName() == _BANNER_SLOT_NAME:
            slot.setVisible(visible)

    def show_message(self, text: str) -> None:
        self._message.setText(text)
        self._set_slot_visible(True)
        self.show()

    def _dismiss(self) -> None:
        self.hide()
        self._set_slot_visible(False)
        if self._on_dismiss is not None:
            self._on_dismiss()


def create_status_banner_slot() -> tuple[QWidget, StatusBanner]:
    """Host with outer margins; hides with the banner."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    from youtube_downloader.ui_qt.theme_tokens import SPACE_MD, SPACE_SM

    slot = QWidget()
    slot.setObjectName(_BANNER_SLOT_NAME)
    slot.hide()
    layout = QVBoxLayout(slot)
    layout.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
    layout.setSpacing(0)
    banner = StatusBanner()
    layout.addWidget(banner)
    return slot, banner
