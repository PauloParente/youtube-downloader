"""Line edit that accepts dragged URLs."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLineEdit

from youtube_downloader.core.metadata import is_youtube_url
from youtube_downloader.core.text_utils import extract_url_from_drop_text


class UrlDropLineEdit(QLineEdit):
    def __init__(
        self,
        on_url_dropped: Callable[[str], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._on_url_dropped = on_url_dropped
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        parts: list[str] = []
        if mime.hasUrls():
            for url in mime.urls():
                parts.append(url.toString())
        if mime.hasText():
            parts.append(mime.text())
        combined = "\n".join(parts)
        found = extract_url_from_drop_text(combined)
        if found and is_youtube_url(found):
            self._on_url_dropped(found)
            event.acceptProposedAction()
