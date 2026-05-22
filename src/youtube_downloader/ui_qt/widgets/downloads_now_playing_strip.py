"""Compact 'now playing' strip on the Downloads screen during an active job."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.widgets.buttons import LinkButton
from youtube_downloader.ui_qt.widgets.card import Card
from youtube_downloader.ui_qt.widgets.common import muted_label, secondary_label


class DownloadsNowPlayingStrip(Card):
    def __init__(
        self,
        *,
        on_open_queue: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.hide()
        body = self.body_layout
        row = QHBoxLayout()
        row.setSpacing(12)

        col = QVBoxLayout()
        col.setSpacing(4)
        self._title = QLabel("Baixando…")
        self._title.setObjectName("sectionTitle")
        col.addWidget(self._title)
        self._status = secondary_label("")
        col.addWidget(self._status)
        row.addLayout(col, stretch=1)

        right = QVBoxLayout()
        right.setSpacing(4)
        self._percent = muted_label("0%")
        self._percent.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        right.addWidget(self._percent)
        if on_open_queue is not None:
            self._queue_link = LinkButton("Ver na Fila")
            self._queue_link.clicked.connect(on_open_queue)
            right.addWidget(
                self._queue_link,
                alignment=Qt.AlignmentFlag.AlignRight,
            )
        else:
            self._queue_link = None
        row.addLayout(right)
        body.addLayout(row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        body.addWidget(self._progress)

    def set_active(
        self,
        *,
        title: str,
        status: str = "",
        percent: Optional[float] = None,
    ) -> None:
        self._title.setText(title.strip() or "Baixando…")
        self._status.setText(status.strip())
        if percent is not None:
            value = max(0, min(100, int(percent * 100)))
            self._progress.setValue(value)
            self._percent.setText(f"{value}%")
        else:
            self._progress.setValue(0)
            self._percent.setText("0%")
        self.show()

    def set_idle(self) -> None:
        self.hide()

    def update_progress(
        self, *, status: str = "", percent: Optional[float] = None, title: str = ""
    ) -> None:
        if title:
            self._title.setText(title.strip())
        if status:
            self._status.setText(status.strip())
        if percent is not None:
            value = max(0, min(100, int(percent * 100)))
            self._progress.setValue(value)
            self._percent.setText(f"{value}%")
