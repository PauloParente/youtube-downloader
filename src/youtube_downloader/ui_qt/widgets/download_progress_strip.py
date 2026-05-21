"""Contextual progress bar shown during download on Downloads screen."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.icons import themed_icon
from youtube_downloader.ui_qt.widgets.buttons import GhostButton
from youtube_downloader.ui_qt.widgets.thumbnail import ThumbnailLabel

STRIP_THUMB_SIZE = (64, 36)


class DownloadProgressStrip(QFrame):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.setObjectName("progressStrip")
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(8)

        context_row = QHBoxLayout()
        context_row.setSpacing(10)
        self._thumb = ThumbnailLabel(*STRIP_THUMB_SIZE)
        context_row.addWidget(self._thumb)
        self._title = QLabel()
        self._title.setWordWrap(True)
        self._title.setObjectName("previewTitle")
        context_row.addWidget(self._title, stretch=1)
        layout.addLayout(context_row)

        row = QHBoxLayout()
        self._message = QLabel()
        row.addWidget(self._message, stretch=1)
        self._percent_label = QLabel("0%")
        row.addWidget(self._percent_label)
        self._cancel_btn = GhostButton("Cancelar")
        self._cancel_btn.clicked.connect(on_cancel)
        row.addWidget(self._cancel_btn)
        layout.addLayout(row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

    def set_active(self, active: bool) -> None:
        if active:
            self.show()
        else:
            self.hide()

    def set_context(self, title: str, thumb_pixmap: Optional[QPixmap] = None) -> None:
        self._title.setText(title.strip() or "Baixando…")
        if thumb_pixmap is not None and not thumb_pixmap.isNull():
            self._thumb.set_pixmap(thumb_pixmap)
        else:
            self._thumb.set_pixmap(themed_icon("video", 28).pixmap(28, 28))

    def set_message(self, text: str) -> None:
        self._message.setText(text)

    def set_indeterminate(self, indeterminate: bool) -> None:
        if indeterminate:
            self._progress.setRange(0, 0)
            self._percent_label.setText("…")
        else:
            self._progress.setRange(0, 100)
            if self._progress.value() == 0:
                self._percent_label.setText("0%")

    def set_percent(self, percent: Optional[float]) -> None:
        if self._progress.minimum() == 0 and self._progress.maximum() == 0:
            self.set_indeterminate(False)
        if percent is None:
            return
        value = int(percent * 100)
        self._progress.setValue(value)
        self._percent_label.setText(f"{value}%")
