"""Compact horizontal row: thumbnail, text, optional action buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.widgets.common import set_text_class
from youtube_downloader.ui_qt.widgets.thumbnail import ThumbnailLabel

DEFAULT_THUMB = (128, 72)


class CompactMediaRow(QFrame):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        thumb_size: tuple[int, int] = DEFAULT_THUMB,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("compactRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(12)

        self._thumb = ThumbnailLabel(*thumb_size)
        layout.addWidget(self._thumb)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title = QLabel()
        self._title.setWordWrap(True)
        self._title.setObjectName("previewTitle")
        text_col.addWidget(self._title)
        self._meta = QLabel()
        set_text_class(self._meta, "muted")
        self._meta.setWordWrap(True)
        text_col.addWidget(self._meta)
        layout.addLayout(text_col, stretch=1)

        self._actions_host = QWidget()
        self._actions_layout = QHBoxLayout(self._actions_host)
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(4)
        layout.addWidget(self._actions_host, alignment=Qt.AlignmentFlag.AlignTop)

    @property
    def actions_layout(self) -> QHBoxLayout:
        return self._actions_layout

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_meta(self, text: str) -> None:
        self._meta.setText(text)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._thumb.set_pixmap(pixmap)

    def set_placeholder(self, text: str = "") -> None:
        self._thumb.set_placeholder_text(text)

    def clear_actions(self) -> None:
        while self._actions_layout.count():
            item = self._actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
