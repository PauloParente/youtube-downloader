"""Queue view — now playing and pending items."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import VideoPreview, format_duration
from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.preview_cache import CARD_THUMB_SIZE, pil_rgb_from_bytes
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui_qt.theme import ACCENT
from youtube_downloader.ui_qt.util import pixmap_from_bytes, pixmap_from_pil, schedule

logger = get_logger(__name__)

THUMB_DISPLAY_SIZE = (240, 135)
QUEUE_URL_TRUNCATE = 58
STRUCTURE_DEBOUNCE_MS = 150
IDLE_NOW_PLAYING = "Nenhum download em andamento"
DEFAULT_NOW_STATUS = "Aguardando…"
LOADING_TITLE = "Carregando…"


@dataclass
class _PendingCardUi:
    frame: QWidget
    title_label: QLabel
    meta_label: QLabel
    thumb_host: QWidget
    index: int


class QueueView(QWidget):
    def __init__(
        self,
        *,
        get_queue_snapshot: Callable[[], list[str]],
        get_cached_preview: Callable[[str], Optional[VideoPreview]],
        get_card_thumb: Callable[[str], Optional[Image.Image]],
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
        self._cards_by_url: dict[str, _PendingCardUi] = {}
        self._structure_timer_pending = False
        self._build_ui()
        self.refresh_structure()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(QLabel("<b style='font-size:22px'>Fila</b>"))
        self._subtitle = QLabel("Acompanhe o download atual e os próximos da fila.")
        layout.addWidget(self._subtitle)

        now_card = QFrame()
        now_card.setObjectName("card")
        now_layout = QVBoxLayout(now_card)
        now_layout.addWidget(QLabel("<b>Baixando agora</b>"))
        row = QHBoxLayout()
        self._now_thumb = QLabel()
        self._now_thumb.setFixedSize(*THUMB_DISPLAY_SIZE)
        self._now_thumb.setStyleSheet("background-color: #2a2a2a; border-radius: 6px;")
        row.addWidget(self._now_thumb)
        col = QVBoxLayout()
        self._now_title = QLabel(IDLE_NOW_PLAYING)
        self._now_title.setWordWrap(True)
        self._now_url = QLabel()
        self._now_url.setProperty("class", "muted")
        col.addWidget(self._now_title)
        col.addWidget(self._now_url)
        status_row = QHBoxLayout()
        self._now_status = QLabel()
        self._now_pct = QLabel("0%")
        status_row.addWidget(self._now_status, stretch=1)
        status_row.addWidget(self._now_pct)
        col.addLayout(status_row)
        row.addLayout(col, stretch=1)
        now_layout.addLayout(row)
        self._now_progress = QProgressBar()
        self._now_progress.setRange(0, 100)
        now_layout.addWidget(self._now_progress)
        actions = QHBoxLayout()
        self._cancel_btn = QPushButton("✕  Cancelar")
        self._cancel_btn.clicked.connect(self._on_cancel_download)
        self._cancel_btn.setEnabled(False)
        actions.addWidget(self._cancel_btn)
        self._skip_btn = QPushButton("⏭  Pular")
        self._skip_btn.clicked.connect(self._on_skip_download)
        self._skip_btn.setEnabled(False)
        actions.addWidget(self._skip_btn)
        actions.addStretch()
        now_layout.addLayout(actions)
        layout.addWidget(now_card)

        pending_card = QFrame()
        pending_card.setObjectName("card")
        pending_layout = QVBoxLayout(pending_card)
        self._pending_title = QLabel("<b>Na fila</b>")
        pending_layout.addWidget(self._pending_title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(400)
        self._pending_host = QWidget()
        self._pending_layout = QVBoxLayout(self._pending_host)
        self._pending_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._pending_host)
        pending_layout.addWidget(scroll)
        self._empty_label: Optional[QLabel] = None
        layout.addWidget(pending_card, stretch=1)

    def set_thumbnail_bytes(self, data: Optional[bytes]) -> None:
        if not data:
            self._now_thumb.clear()
            return
        px = pixmap_from_bytes(data, THUMB_DISPLAY_SIZE)
        if px:
            self._now_thumb.setPixmap(px)

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
        if active:
            display = (title or "").strip() or truncate_text(url, 48) or "Baixando…"
            self._now_title.setText(display)
            self._now_url.setText(truncate_text(url, QUEUE_URL_TRUNCATE) if url else "")
            self._now_status.setText(status or DEFAULT_NOW_STATUS)
            if percent is not None:
                self._now_progress.setValue(int(percent * 100))
                self._now_pct.setText(f"{int(percent * 100)}%")
            self._now_progress.show()
            self._now_pct.show()
        else:
            self._now_title.setText(IDLE_NOW_PLAYING)
            self._now_url.setText("")
            self._now_status.setText("")
            self._now_progress.setValue(0)
            self._now_pct.setText("0%")
        self._sync_action_buttons()

    def apply_progress_event(self, event: ProgressEvent) -> None:
        if not self._is_downloading:
            return
        if event.event_type == EventType.PROGRESS:
            if event.percent is not None:
                self._now_progress.setValue(int(event.percent * 100))
                self._now_pct.setText(f"{int(event.percent * 100)}%")
            if event.message:
                self._now_status.setText(event.message)
            if event.title:
                self._now_title.setText(event.title)
        elif event.event_type == EventType.LOG:
            if event.message:
                self._now_status.setText(event.message)
            if event.percent is not None:
                self._now_progress.setValue(int(event.percent * 100))
                self._now_pct.setText(f"{int(event.percent * 100)}%")
            if event.title:
                self._now_title.setText(event.title)
        elif event.event_type == EventType.DONE:
            self._now_progress.setValue(100)
            self._now_pct.setText("100%")
            if event.message:
                self._now_status.setText(event.message)
        elif event.event_type == EventType.ERROR and event.message:
            self._now_status.setText(event.message)
        elif event.event_type == EventType.CANCELLED:
            self._now_status.setText("Cancelando…")

    def _sync_action_buttons(self) -> None:
        pending = len(self._get_queue_snapshot())
        if self._is_downloading:
            self._cancel_btn.setEnabled(True)
            self._skip_btn.setEnabled(pending > 0)
            if pending:
                self._skip_btn.setStyleSheet(f"background-color: {ACCENT};")
        else:
            self._cancel_btn.setEnabled(False)
            self._skip_btn.setEnabled(False)

    def _update_header_labels(self, count: int) -> None:
        suffix = f" ({count})" if count else ""
        self._pending_title.setText(f"<b>Na fila{suffix}</b>")
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
            if self._empty_label is None:
                self._empty_label = QLabel("Nenhum link na fila")
                self._pending_layout.addWidget(self._empty_label)
            else:
                self._empty_label.show()
            self._sync_action_buttons()
            return
        if self._empty_label is not None:
            self._empty_label.hide()
        for index, url in enumerate(urls):
            cleaned = url.strip()
            if cleaned not in self._cards_by_url:
                self._create_pending_card(index, cleaned, self._get_cached_preview(cleaned))
            else:
                self._reindex_card(cleaned, index)
        self._sync_action_buttons()

    def update_card(self, url: str) -> None:
        cleaned = url.strip()
        ui = self._cards_by_url.get(cleaned)
        if ui is None:
            return
        preview = self._get_cached_preview(cleaned)
        ui.title_label.setText(self._card_title(cleaned, preview))
        ui.meta_label.setText(f"#{ui.index + 1} · {self._card_duration(preview)}")
        self._apply_thumb(ui.thumb_host, cleaned, preview)

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

    def _apply_thumb(
        self, host: QWidget, url: str, preview: Optional[VideoPreview]
    ) -> None:
        layout = host.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        pil_thumb = self._get_card_thumb(url)
        label = QLabel()
        label.setFixedSize(*CARD_THUMB_SIZE)
        if pil_thumb is not None:
            label.setPixmap(pixmap_from_pil(pil_thumb, CARD_THUMB_SIZE))
        elif preview and preview.thumbnail_bytes:
            try:
                img = pil_rgb_from_bytes(preview.thumbnail_bytes)
                label.setPixmap(pixmap_from_pil(img, CARD_THUMB_SIZE))
            except Exception:
                label.setText("▶")
        else:
            label.setText("▶")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if host.layout() is None:
            hl = QVBoxLayout(host)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(label)
        else:
            host.layout().addWidget(label)

    def _create_pending_card(
        self, index: int, url: str, preview: Optional[VideoPreview]
    ) -> None:
        card = QWidget()
        card.setObjectName("card")
        h = QHBoxLayout(card)
        thumb_host = QWidget()
        thumb_host.setFixedSize(CARD_THUMB_SIZE[0], CARD_THUMB_SIZE[1])
        self._apply_thumb(thumb_host, url, preview)
        h.addWidget(thumb_host)
        body = QVBoxLayout()
        title_label = QLabel(self._card_title(url, preview))
        title_label.setWordWrap(True)
        meta_label = QLabel(f"#{index + 1} · {self._card_duration(preview)}")
        body.addWidget(title_label)
        body.addWidget(meta_label)
        h.addLayout(body, stretch=1)
        rem = QPushButton("🗑")
        rem.setFixedWidth(40)
        rem.clicked.connect(lambda: self._remove_by_url(url))
        h.addWidget(rem)
        self._pending_layout.addWidget(card)
        self._cards_by_url[url] = _PendingCardUi(
            frame=card,
            title_label=title_label,
            meta_label=meta_label,
            thumb_host=thumb_host,
            index=index,
        )

    def _reindex_card(self, url: str, index: int) -> None:
        ui = self._cards_by_url.get(url)
        if ui is None:
            return
        ui.index = index
        preview = self._get_cached_preview(url)
        ui.meta_label.setText(f"#{index + 1} · {self._card_duration(preview)}")

    def _destroy_card(self, url: str) -> None:
        ui = self._cards_by_url.pop(url, None)
        if ui is not None:
            ui.frame.deleteLater()

    def _remove_by_url(self, url: str) -> None:
        urls = self._get_queue_snapshot()
        cleaned = url.strip()
        try:
            index = next(i for i, u in enumerate(urls) if u.strip() == cleaned)
        except StopIteration:
            return
        self._on_remove_queue_at(index)
