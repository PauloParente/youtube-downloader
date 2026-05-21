"""Queue view — now playing and pending items."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import VideoPreview, format_duration
from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.preview_cache import CARD_THUMB_SIZE, pil_rgb_from_bytes
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui_qt.icons import icon_on_button
from youtube_downloader.ui_qt.util import pixmap_from_pil, schedule
from youtube_downloader.ui_qt.widgets import (
    Card,
    CompactMediaRow,
    EmptyState,
    IconButton,
    PageHeader,
    QueueNowPlayingCard,
    SectionTitle,
    apply_page_margins,
)

logger = get_logger(__name__)

QUEUE_URL_TRUNCATE = 58
STRUCTURE_DEBOUNCE_MS = 150
LOADING_TITLE = "Carregando…"


@dataclass
class _PendingCardUi:
    row: CompactMediaRow
    index: int


class QueueView(QWidget):
    def __init__(
        self,
        *,
        get_queue_snapshot: Callable[[], list[str]],
        get_cached_preview: Callable[[str], Optional[VideoPreview]],
        get_card_thumb: Callable[[str], Optional[object]],
        is_preview_pending: Callable[[str], bool],
        on_remove_queue_at: Callable[[int], None],
        on_cancel_download: Callable[[], None],
        on_skip_download: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_queue_snapshot = get_queue_snapshot
        self._get_cached_preview = get_cached_preview
        self._get_card_thumb = get_card_thumb
        self._is_preview_pending = is_preview_pending
        self._on_remove_queue_at = on_remove_queue_at
        self._on_cancel_download = on_cancel_download
        self._on_skip_download = on_skip_download
        self._is_downloading = False
        self._now_playing_url = ""
        self._cards_by_url: dict[str, _PendingCardUi] = {}
        self._structure_timer_pending = False
        self._build_ui()
        self.refresh_structure()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        header = PageHeader(
            "Fila",
            "Acompanhe o download atual e os próximos da fila.",
        )
        layout.addWidget(header)
        self._subtitle = header.subtitle_label

        self._now_playing = QueueNowPlayingCard(
            on_cancel=self._on_cancel_download,
            on_skip=self._on_skip_download,
        )
        layout.addWidget(self._now_playing)

        pending_card = Card()
        pending_layout = pending_card.body_layout
        self._pending_title = SectionTitle("Na fila")
        pending_layout.addWidget(self._pending_title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._pending_scroll = scroll
        scroll.setMinimumHeight(200)
        self._pending_host = QWidget()
        self._pending_layout = QVBoxLayout(self._pending_host)
        self._pending_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._pending_host)
        pending_layout.addWidget(scroll)
        self._empty_widget: Optional[EmptyState] = None
        layout.addWidget(pending_card, stretch=1)

    def _apply_now_playing_thumb(self, url: str) -> None:
        self._now_playing.apply_thumbnail(
            url,
            get_card_thumb=self._get_card_thumb,
            get_cached_preview=self._get_cached_preview,
            is_preview_pending=self._is_preview_pending,
        )

    def set_now_playing(
        self,
        *,
        active: bool,
        url: str = "",
        title: str = "",
        status: str = "",
        percent: Optional[float] = None,
    ) -> None:
        self._is_downloading = active
        cleaned_url = url.strip()
        if active:
            self._now_playing_url = cleaned_url
            display = (title or "").strip() or truncate_text(url, 48) or "Baixando…"
            self._now_playing.set_active(
                title=display,
                meta=truncate_text(url, QUEUE_URL_TRUNCATE) if url else "",
                status=status,
                percent=percent,
            )
            if cleaned_url:
                self._apply_now_playing_thumb(cleaned_url)
        else:
            self._now_playing_url = ""
            self._now_playing.set_idle()
        self._sync_action_buttons()

    def apply_progress_event(self, event: ProgressEvent) -> None:
        if not self._is_downloading:
            return
        if event.event_type == EventType.PROGRESS:
            if event.percent is not None:
                self._now_playing.set_percent(event.percent)
            if event.message:
                self._now_playing.set_status(event.message)
            if event.title:
                self._now_playing.set_title(event.title)
        elif event.event_type == EventType.LOG:
            if event.message:
                self._now_playing.set_status(event.message)
            if event.percent is not None:
                self._now_playing.set_percent(event.percent)
            if event.title:
                self._now_playing.set_title(event.title)
        elif event.event_type == EventType.DONE:
            self._now_playing.set_percent(1.0)
            if event.message:
                self._now_playing.set_status(event.message)
        elif event.event_type == EventType.ERROR and event.message:
            self._now_playing.set_status(event.message)
        elif event.event_type == EventType.CANCELLED:
            self._now_playing.set_status("Cancelando…")

    def _sync_action_buttons(self) -> None:
        pending = len(self._get_queue_snapshot())
        if self._is_downloading:
            self._now_playing.set_cancel_enabled(True)
            self._now_playing.set_skip_enabled(pending > 0, emphasize=pending > 0)
        else:
            self._now_playing.set_cancel_enabled(False)
            self._now_playing.set_skip_enabled(False)

    def _update_header_labels(self, count: int) -> None:
        suffix = f" ({count})" if count else ""
        self._pending_title.setText(f"Na fila{suffix}")
        if self._subtitle is not None:
            self._subtitle.setText(
                f"{count} vídeo(s) aguardando na fila."
                if count
                else "Acompanhe o download atual e os próximos da fila."
            )

    def refresh(self) -> None:
        if not self._structure_timer_pending:
            self._structure_timer_pending = True
            schedule(self, STRUCTURE_DEBOUNCE_MS, self._do_refresh_structure)

    def refresh_structure(self) -> None:
        self._structure_timer_pending = False
        self._do_refresh_structure()

    def reconcile_pending(self) -> None:
        self._do_refresh_structure()

    def _do_refresh_structure(self) -> None:
        self._structure_timer_pending = False
        urls = self._get_queue_snapshot()
        self._update_header_labels(len(urls))
        pending_set = {u.strip() for u in urls}
        for url in list(self._cards_by_url.keys()):
            if url not in pending_set:
                self._destroy_card(url)
        if not urls:
            self._pending_scroll.setMinimumHeight(200)
            if self._empty_widget is None:
                self._empty_widget = EmptyState(
                    "queue",
                    "Nenhum link na fila",
                    "Use + Fila na tela Downloads para enfileirar vídeos.",
                )
                self._pending_layout.addWidget(self._empty_widget)
            else:
                self._empty_widget.show()
            self._sync_action_buttons()
            return
        self._pending_scroll.setMinimumHeight(400)
        if self._empty_widget is not None:
            self._empty_widget.hide()
        for index, url in enumerate(urls):
            cleaned = url.strip()
            if cleaned not in self._cards_by_url:
                self._create_pending_card(index, cleaned, self._get_cached_preview(cleaned))
            else:
                self._reindex_card(cleaned, index)
        self._sync_action_buttons()

    def update_card(self, url: str) -> None:
        cleaned = url.strip()
        if cleaned and cleaned == self._now_playing_url:
            self._apply_now_playing_thumb(cleaned)
        ui = self._cards_by_url.get(cleaned)
        if ui is None:
            return
        preview = self._get_cached_preview(cleaned)
        ui.row.set_title(self._card_title(cleaned, preview))
        ui.row.set_meta(f"#{ui.index + 1} · {self._card_duration(preview)}")
        self._apply_thumb_row(ui.row, cleaned, preview)

    def _card_title(self, url: str, preview: Optional[VideoPreview]) -> str:
        if preview and preview.title and preview.title.strip():
            return preview.title.strip()
        if self._is_preview_pending(url) or self._get_cached_preview(url) is None:
            return LOADING_TITLE
        return truncate_text(url, 52)

    @staticmethod
    def _card_duration(preview: Optional[VideoPreview]) -> str:
        if preview:
            text = format_duration(preview.duration_seconds)
            if text:
                return text
        return "—"

    def _apply_thumb_row(
        self, row: CompactMediaRow, url: str, preview: Optional[VideoPreview]
    ) -> None:
        pil_thumb = self._get_card_thumb(url)
        if pil_thumb is not None:
            row.set_pixmap(pixmap_from_pil(pil_thumb, CARD_THUMB_SIZE))
        elif preview and preview.thumbnail_bytes:
            try:
                img = pil_rgb_from_bytes(preview.thumbnail_bytes)
                row.set_pixmap(pixmap_from_pil(img, CARD_THUMB_SIZE))
            except Exception:
                row.set_placeholder("…")
        else:
            row.set_placeholder("…")

    def _create_pending_card(
        self, index: int, url: str, preview: Optional[VideoPreview]
    ) -> None:
        row = CompactMediaRow(thumb_size=CARD_THUMB_SIZE)
        row.set_title(self._card_title(url, preview))
        row.set_meta(f"#{index + 1} · {self._card_duration(preview)}")
        self._apply_thumb_row(row, url, preview)
        rem = IconButton(tooltip="Remover da fila")
        icon_on_button(rem, "trash", size=18)
        rem.clicked.connect(lambda: self._remove_by_url(url))
        row.actions_layout.addWidget(rem)
        self._pending_layout.addWidget(row)
        self._cards_by_url[url] = _PendingCardUi(row=row, index=index)

    def _reindex_card(self, url: str, index: int) -> None:
        ui = self._cards_by_url.get(url)
        if ui is None:
            return
        ui.index = index
        preview = self._get_cached_preview(url)
        ui.row.set_meta(f"#{index + 1} · {self._card_duration(preview)}")

    def _destroy_card(self, url: str) -> None:
        ui = self._cards_by_url.pop(url, None)
        if ui is not None:
            ui.row.deleteLater()

    def _remove_by_url(self, url: str) -> None:
        urls = self._get_queue_snapshot()
        cleaned = url.strip()
        try:
            index = next(i for i, u in enumerate(urls) if u.strip() == cleaned)
        except StopIteration:
            return
        self._on_remove_queue_at(index)
