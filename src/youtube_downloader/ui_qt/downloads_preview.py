"""Preview panel for the Downloads screen."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QVBoxLayout, QWidget

from youtube_downloader.core.download_errors import humanize_ytdlp_error
from youtube_downloader.core.logging_config import clear_preview_cache, get_logger
from youtube_downloader.core.metadata import VideoPreview, fetch_preview, is_youtube_url
from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.preview_cache import PreviewCache
from youtube_downloader.ui_qt.event_bridge import EventBridge
from youtube_downloader.ui_qt.util import schedule
from youtube_downloader.ui_qt.widgets import EmptyState, MediaPreviewRow, PreviewSkeleton
from youtube_downloader.ui_qt.widgets.download_options_bar import DownloadOptionsBar
from youtube_downloader.ui_qt.widgets.download_alert import DownloadAlert

logger = get_logger(__name__)

PREVIEW_DEBOUNCE_MS = 600


class DownloadsPreviewPanel:
    """Preview skeleton + media card (options inside card when loaded)."""

    def __init__(
        self,
        host: QWidget,
        *,
        get_url: Callable[[], str],
        event_bridge: EventBridge,
        preview_cache: PreviewCache,
        is_downloading: Callable[[], bool],
        on_open_queue: Callable[[], None] | None = None,
    ) -> None:
        self._host = host
        self._get_url = get_url
        self._event_bridge = event_bridge
        self._preview_cache = preview_cache
        self._is_downloading = is_downloading
        self._on_open_queue = on_open_queue
        self._preview_request_id = 0
        self._current_preview: Optional[VideoPreview] = None

        self._section: Optional[QWidget] = None
        self._alert: Optional[DownloadAlert] = None
        self._empty_state: Optional[EmptyState] = None
        self._skeleton: Optional[PreviewSkeleton] = None
        self._media_row: Optional[MediaPreviewRow] = None
        self._fade_anim: Optional[QPropertyAnimation] = None

    @property
    def current_preview(self) -> Optional[VideoPreview]:
        return self._current_preview

    @property
    def preview_title_label(self):
        if self._media_row is not None:
            return self._media_row.title_label
        return None

    @property
    def media_row(self) -> Optional[MediaPreviewRow]:
        return self._media_row

    def show_alert(self, text: str) -> None:
        if self._alert is not None:
            self._alert.show_alert(text)

    def hide_alert(self) -> None:
        if self._alert is not None:
            self._alert.hide_alert()

    def attach_to(
        self,
        parent_layout: QVBoxLayout,
        *,
        options_bar: DownloadOptionsBar,
    ) -> MediaPreviewRow:
        self._section = QWidget()
        section_layout = QVBoxLayout(self._section)
        section_layout.setContentsMargins(0, 8, 0, 0)
        section_layout.setSpacing(8)

        self._alert = DownloadAlert(self._section)
        section_layout.addWidget(self._alert)

        self._empty_state = EmptyState(
            "link",
            "Nenhum vídeo selecionado",
            "Cole ou arraste um link do YouTube no campo acima.",
            parent=self._section,
        )
        self._empty_state.hide()
        section_layout.addWidget(self._empty_state)

        self._skeleton = PreviewSkeleton()
        section_layout.addWidget(self._skeleton)

        self._media_row = MediaPreviewRow(on_open_queue=self._on_open_queue)
        self._media_row.attach_options_bar(options_bar)
        self._media_row.hide()
        section_layout.addWidget(self._media_row)

        parent_layout.addWidget(self._section)
        return self._media_row

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

    def _show_skeleton(self, visible: bool) -> None:
        if self._skeleton is not None:
            self._skeleton.setVisible(visible)
            if visible:
                self._skeleton.start_shimmer()
            else:
                self._skeleton.stop_shimmer()

    def _show_media(self, visible: bool) -> None:
        if self._media_row is not None:
            if visible:
                self._fade_in_media_row()
            else:
                self._media_row.hide()

    def _fade_in_media_row(self) -> None:
        if self._media_row is None:
            return
        self._media_row.show()
        effect = QGraphicsOpacityEffect(self._media_row)
        self._media_row.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self._host)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim = anim

        def _cleanup() -> None:
            if self._media_row is not None:
                self._media_row.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        anim.start()

    def _show_preview_loading(self) -> None:
        clear_preview_cache()
        if self._empty_state is not None:
            self._empty_state.hide()
        self._show_skeleton(False)
        if self._media_row is not None:
            self._media_row.set_loading()
            self._show_media(True)

    def _clear_preview(self) -> None:
        self._preview_request_id += 1
        self._current_preview = None
        clear_preview_cache()
        self.hide_alert()
        if self._media_row is not None:
            self._media_row.clear()
            self._media_row.hide()
        url = self._get_url().strip()
        if not url:
            self._show_skeleton(False)
            if self._empty_state is not None:
                self._empty_state.show()
        else:
            if self._empty_state is not None:
                self._empty_state.hide()
            self._show_skeleton(True)

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

        self._show_skeleton(False)
        if self._media_row is None:
            return

        if preview.error:
            self._current_preview = None
            msg = humanize_ytdlp_error(preview.error)
            self._media_row.show_error(msg)
            self.show_alert(msg)
            if self._empty_state is not None:
                self._empty_state.hide()
            self._show_media(True)
            return

        self.hide_alert()
        if self._empty_state is not None:
            self._empty_state.hide()

        self._current_preview = preview
        self._media_row.apply_preview(preview, url=url, request_id=request_id)
        self._show_media(True)
