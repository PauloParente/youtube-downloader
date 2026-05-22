"""Card container."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.theme_tokens import CARD_PADDING, SPACE_SM


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING
        )
        self._layout.setSpacing(SPACE_SM)

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._layout
