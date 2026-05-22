"""Horizontal preview row: thumbnail + title/metadata + optional download options."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from youtube_downloader.core.logging_config import LOG_CACHE_DIR
from youtube_downloader.core.metadata import VideoPreview, format_duration
from youtube_downloader.core.preview_cache import pil_rgb_from_bytes
from youtube_downloader.ui_qt.util import pixmap_from_pil
from youtube_downloader.ui_qt.widgets.buttons import LinkButton
from youtube_downloader.ui_qt.widgets.common import set_text_class
from youtube_downloader.ui_qt.widgets.download_options_bar import DownloadOptionsBar
from youtube_downloader.ui_qt.widgets.section import Separator
from youtube_downloader.ui_qt.widgets.thumbnail import ThumbnailLabel

THUMB_DISPLAY_SIZE = (240, 135)
_LOADING_BASE = "Carregando preview"


class MediaPreviewRow(QFrame):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_open_queue: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._on_open_queue = on_open_queue
        self._cache_id = 0
        self._ellipsis_step = 0
        self._ellipsis_timer = QTimer(self)
        self._ellipsis_timer.setInterval(400)
        self._ellipsis_timer.timeout.connect(self._tick_loading_ellipsis)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        self._thumb = ThumbnailLabel(*THUMB_DISPLAY_SIZE)
        content_row.addWidget(self._thumb)

        col = QVBoxLayout()
        col.setSpacing(4)
        self._title_label = QLabel()
        self._title_label.setWordWrap(True)
        self._title_label.setObjectName("previewTitle")
        self._title_label.setAutoFillBackground(False)
        col.addWidget(self._title_label)

        self._subtitle_label = QLabel()
        self._subtitle_label.setAutoFillBackground(False)
        set_text_class(self._subtitle_label, "secondary")
        col.addWidget(self._subtitle_label)

        self._playlist_chip = LinkButton("")
        self._playlist_chip.hide()
        if on_open_queue is not None:
            self._playlist_chip.clicked.connect(on_open_queue)
        col.addWidget(self._playlist_chip)
        col.addStretch()
        content_row.addLayout(col, stretch=1)
        root.addLayout(content_row)

        self._options_sep = Separator()
        self._options_sep.hide()
        root.addWidget(self._options_sep)

        self._options_host = QWidget()
        self._options_host.setObjectName("previewOptionsHost")
        self._options_host.setAutoFillBackground(False)
        self._options_host.hide()
        self._options_layout = QVBoxLayout(self._options_host)
        self._options_layout.setContentsMargins(0, 12, 0, 0)
        self._options_layout.setSpacing(0)
        root.addWidget(self._options_host)

    def attach_options_bar(self, options_bar: DownloadOptionsBar) -> None:
        while self._options_layout.count():
            item = self._options_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._options_layout.addWidget(options_bar)

    def set_options_visible(self, visible: bool) -> None:
        self._options_sep.setVisible(visible)
        self._options_host.setVisible(visible)

    @property
    def title_label(self) -> QLabel:
        return self._title_label

    def _stop_loading_animation(self) -> None:
        self._ellipsis_timer.stop()
        self._thumb.set_loading(False)

    def _tick_loading_ellipsis(self) -> None:
        self._ellipsis_step = (self._ellipsis_step + 1) % 4
        dots = "." * self._ellipsis_step
        self._title_label.setText(f"{_LOADING_BASE}{dots}")

    def _start_loading_animation(self) -> None:
        self.set_options_visible(False)
        self._ellipsis_step = 0
        self._title_label.setText(_LOADING_BASE)
        self._subtitle_label.setText("")
        self._playlist_chip.hide()
        self._thumb.set_loading(True)
        self._ellipsis_timer.start()

    def set_title(self, text: str) -> None:
        self._stop_loading_animation()
        self._title_label.setText(text)

    def set_meta(self, text: str) -> None:
        self._subtitle_label.setText(text)

    def set_placeholder(self, text: str) -> None:
        self.set_options_visible(False)
        self._stop_loading_animation()
        self._thumb.set_placeholder_text(text)
        if text:
            self._title_label.setText(text)
            self._subtitle_label.setText("")

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._thumb.set_pixmap(pixmap)

    def set_thumb_placeholder(self, text: str = "…") -> None:
        """Update only the thumbnail area (does not change title/meta)."""
        self._stop_loading_animation()
        self._thumb.set_placeholder_text(text)

    def clear(self) -> None:
        self.set_options_visible(False)
        self._stop_loading_animation()
        self._thumb.set_placeholder_text("")
        self._title_label.setText("")
        self._subtitle_label.setText("")
        self._playlist_chip.hide()

    def set_loading(self) -> None:
        self._start_loading_animation()

    def show_error(self, message: str) -> None:
        self.set_options_visible(False)
        self._stop_loading_animation()
        self._thumb.set_placeholder_text("?")
        self._title_label.setText("Preview indisponível")
        self._subtitle_label.setText(message[:120])
        self._playlist_chip.hide()

    def apply_preview(
        self,
        preview: VideoPreview,
        *,
        url: str,
        request_id: Optional[int] = None,
    ) -> None:
        self._cache_id = request_id if request_id is not None else self._cache_id + 1
        if preview.error:
            self.show_error(preview.error)
            return

        self._stop_loading_animation()
        self._title_label.setText(preview.title)
        if preview.is_playlist and preview.playlist_count is not None:
            count = preview.playlist_count
            self._subtitle_label.setText(
                f"{count} vídeos serão enfileirados ao baixar"
            )
            self._playlist_chip.setText(f"Ver fila ({count})")
            self._playlist_chip.show()
            if self._on_open_queue is not None:
                self._playlist_chip.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            channel = preview.uploader or "Canal"
            duration = format_duration(preview.duration_seconds)
            self._subtitle_label.setText(
                f"{channel} · {duration}" if duration else channel
            )
            self._playlist_chip.hide()

        duration_text = format_duration(preview.duration_seconds) or ""
        self._thumb.set_duration_badge(duration_text)

        if preview.thumbnail_bytes:
            try:
                base = pil_rgb_from_bytes(preview.thumbnail_bytes)
                cache_path = LOG_CACHE_DIR / f"preview_{self._cache_id}.jpg"
                base.save(cache_path, "JPEG", quality=90)
                px = pixmap_from_pil(base, THUMB_DISPLAY_SIZE)
                if px is not None:
                    self._thumb.set_pixmap(px)
            except Exception:
                self._thumb.set_placeholder_text("?")
        else:
            self._thumb.set_placeholder_text("")

