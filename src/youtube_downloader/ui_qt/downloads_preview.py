"""Preview panel for the Downloads screen."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Optional

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from youtube_downloader.core.logging_config import LOG_CACHE_DIR, clear_preview_cache, get_logger
from youtube_downloader.core.metadata import VideoPreview, fetch_preview, format_duration, is_youtube_url
from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.preview_cache import PreviewCache, pil_rgb_from_bytes
from youtube_downloader.ui_qt.event_bridge import EventBridge
from youtube_downloader.ui_qt.theme import CARD_BORDER
from youtube_downloader.ui_qt.util import pixmap_from_pil, schedule

logger = get_logger(__name__)

PREVIEW_DEBOUNCE_MS = 600
THUMB_DISPLAY_SIZE = (240, 135)


class DownloadsPreviewPanel:
    def __init__(
        self,
        host: QWidget,
        *,
        get_url: Callable[[], str],
        event_bridge: EventBridge,
        preview_cache: PreviewCache,
        is_downloading: Callable[[], bool],
    ) -> None:
        self._host = host
        self._get_url = get_url
        self._event_bridge = event_bridge
        self._preview_cache = preview_cache
        self._is_downloading = is_downloading
        self._preview_request_id = 0
        self._current_preview: Optional[VideoPreview] = None
        self._debounce_timer_id: Optional[int] = None

        self._placeholder: Optional[QFrame] = None
        self._card: Optional[QFrame] = None
        self._thumb_label: Optional[QLabel] = None
        self._duration_label: Optional[QLabel] = None
        self._title_label: Optional[QLabel] = None
        self._subtitle_label: Optional[QLabel] = None
        self.mid: Optional[QWidget] = None

    @property
    def current_preview(self) -> Optional[VideoPreview]:
        return self._current_preview

    @property
    def preview_title_label(self) -> Optional[QLabel]:
        return self._title_label

    @property
    def preview_frame(self) -> Optional[QFrame]:
        return self._card

    def build_into(self, parent: QWidget) -> QFrame:
        self.mid = parent
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QFrame()
        self._placeholder.setObjectName("card")
        ph_layout = QVBoxLayout(self._placeholder)
        ph_layout.addWidget(QLabel("O preview do vídeo aparecerá aqui", alignment=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(self._placeholder)

        self._card = QFrame()
        self._card.setObjectName("card")
        card_layout = QVBoxLayout(self._card)

        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(*THUMB_DISPLAY_SIZE)
        self._thumb_label.setStyleSheet("background-color: #2a2a2a; border-radius: 6px;")
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._thumb_label)

        self._duration_label = QLabel()
        self._duration_label.setStyleSheet(
            "background-color: #000; color: white; padding: 2px 6px; border-radius: 4px;"
        )
        self._title_label = QLabel()
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._subtitle_label = QLabel()
        self._subtitle_label.setProperty("class", "secondary")
        card_layout.addWidget(self._title_label)
        card_layout.addWidget(self._subtitle_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {CARD_BORDER};")
        card_layout.addWidget(sep)

        self._card.hide()
        layout.addWidget(self._card)
        return self._card

    def clear(self) -> None:
        self._clear_preview()

    def cancel_pending_schedule(self) -> None:
        pass

    def schedule_preview(self) -> None:
        if self._is_downloading():
            return
        schedule(self._host, PREVIEW_DEBOUNCE_MS, self._run_preview_fetch)

    def handle_progress_event(self, event: ProgressEvent) -> bool:
        if event.event_type == EventType.PREVIEW_READY:
            if event.preview is not None and event.preview_url:
                self._apply_preview(
                    event.preview, event.preview_url, request_id=event.preview_request_id
                )
            return True
        if event.event_type == EventType.PREVIEW_CLEAR:
            self._clear_preview()
            return True
        return False

    def _run_preview_fetch(self) -> None:
        if self._is_downloading():
            return
        url = self._get_url().strip()
        if not url or not is_youtube_url(url):
            self._clear_preview()
            return
        self._preview_request_id += 1
        request_id = self._preview_request_id
        self._show_preview_loading()

        def worker() -> None:
            preview = fetch_preview(url)
            self._event_bridge.emit_progress(
                ProgressEvent(
                    event_type=EventType.PREVIEW_READY,
                    preview=preview,
                    preview_url=url,
                    preview_request_id=request_id,
                )
            )

        threading.Thread(target=worker, daemon=True).start()

    def _show_preview_panel(self, visible: bool) -> None:
        if self._card is None or self._placeholder is None:
            return
        self._card.setVisible(visible)
        self._placeholder.setVisible(not visible)

    def _show_preview_loading(self) -> None:
        clear_preview_cache()
        self._show_preview_panel(True)
        if self._thumb_label:
            self._thumb_label.setText("…")
        if self._title_label:
            self._title_label.setText("Carregando preview…")
        if self._subtitle_label:
            self._subtitle_label.setText("")

    def _clear_preview(self) -> None:
        self._preview_request_id += 1
        self._current_preview = None
        clear_preview_cache()
        if self._thumb_label:
            self._thumb_label.clear()
        if self._title_label:
            self._title_label.setText("")
        if self._subtitle_label:
            self._subtitle_label.setText("")
        if self._duration_label:
            self._duration_label.setText("")
        self._show_preview_panel(False)

    def _apply_preview(
        self, preview: VideoPreview, url: str, request_id: Optional[int] = None
    ) -> None:
        if request_id is not None and request_id != self._preview_request_id:
            return
        if self._get_url().strip() != url:
            return
        if not preview.error:
            self._preview_cache.put(preview)
        if self._is_downloading():
            return
        if preview.error:
            self._show_preview_panel(True)
            if self._thumb_label:
                self._thumb_label.setText("?")
            if self._title_label:
                self._title_label.setText("Preview indisponível")
            if self._subtitle_label:
                self._subtitle_label.setText(preview.error[:120])
            return

        self._current_preview = preview
        self._show_preview_panel(True)
        if self._title_label:
            self._title_label.setText(preview.title)
        if preview.is_playlist and preview.playlist_count is not None:
            if self._subtitle_label:
                self._subtitle_label.setText(f"Playlist · {preview.playlist_count} vídeos")
        else:
            channel = preview.uploader or "Canal"
            duration = format_duration(preview.duration_seconds)
            if self._subtitle_label:
                self._subtitle_label.setText(
                    f"{channel} · {duration}" if duration else channel
                )
        if self._duration_label:
            self._duration_label.setText(format_duration(preview.duration_seconds) or "")

        if preview.thumbnail_bytes and self._thumb_label:
            try:
                base = pil_rgb_from_bytes(preview.thumbnail_bytes)
                cache_id = request_id if request_id is not None else self._preview_request_id
                cache_path = LOG_CACHE_DIR / f"preview_{cache_id}.jpg"
                base.save(cache_path, "JPEG", quality=90)
                px = pixmap_from_pil(base, THUMB_DISPLAY_SIZE)
                self._thumb_label.setPixmap(px)
                self._thumb_label.setText("")
            except Exception:
                logger.exception("Falha ao exibir thumbnail")
                self._thumb_label.setText("?")
