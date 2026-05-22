"""Queue view — now playing, activity log, and pending items."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QResizeEvent, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import VideoPreview, format_duration
from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.preview_cache import CARD_THUMB_SIZE, pil_rgb_from_bytes
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui_qt.icons import icon_on_button
from youtube_downloader.ui_qt.layout_breakpoints import QueueLayoutMode, queue_layout_mode
from youtube_downloader.ui_qt.theme_tokens import (
    ICON_MD,
    QUEUE_PENDING_SCROLL_MIN_HEIGHT,
    QUEUE_PENDING_SCROLL_MIN_HEIGHT_WITH_ITEMS,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
)
from youtube_downloader.ui_qt.util import pixmap_from_pil, schedule
from youtube_downloader.ui_qt.widgets import (
    ActivityLogPanel,
    Card,
    CompactMediaRow,
    EmptyState,
    GhostButton,
    IconButton,
    LinkButton,
    PageHeader,
    QueueNowPlayingCard,
    SectionTitle,
    apply_layout_spacing,
    apply_page_margins,
    muted_label,
)

logger = get_logger(__name__)

QUEUE_URL_TRUNCATE = 58
STRUCTURE_DEBOUNCE_MS = 150
LOADING_TITLE = "Carregando…"
LEFT_COLUMN_STRETCH = 2
RIGHT_COLUMN_STRETCH = 1


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
        on_clear_queue: Callable[[], None] | None = None,
        on_open_downloads: Callable[[], None] | None = None,
        activity_log_expanded: bool = True,
        on_activity_expanded_changed: Callable[[], None] | None = None,
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
        self._on_clear_queue = on_clear_queue
        self._on_open_downloads = on_open_downloads
        self._on_activity_expanded_changed = on_activity_expanded_changed
        self._is_downloading = False
        self._last_percent: Optional[float] = None
        self._now_playing_url = ""
        self._collapsed_activity_after_success = False
        self._cards_by_url: dict[str, _PendingCardUi] = {}
        self._structure_timer_pending = False
        self._columns_layout_mode: QueueLayoutMode | None = None
        self._mode_stack: QStackedWidget | None = None
        self._wide_page: QWidget | None = None
        self._wide_layout: QHBoxLayout | None = None
        self._compact_tabs: QTabWidget | None = None
        self._build_ui()
        self._bind_shortcuts()
        self._activity_panel.set_expanded(activity_log_expanded)
        self.refresh_structure()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        header = PageHeader(
            "Fila",
            "Acompanhe o download atual, o log e os próximos da fila.",
        )
        layout.addWidget(header)
        self._subtitle = header.subtitle_label

        self._summary_banner = QFrame()
        self._summary_banner.setObjectName("statusBanner")
        summary_layout = QHBoxLayout(self._summary_banner)
        summary_layout.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        self._summary_label = muted_label("")
        summary_layout.addWidget(self._summary_label, stretch=1)
        layout.addWidget(self._summary_banner)
        self._summary_banner.hide()

        main_column = QVBoxLayout()
        apply_layout_spacing(main_column)
        self._now_playing = QueueNowPlayingCard(
            on_cancel=self._on_cancel_download,
            on_skip=self._on_skip_download,
        )
        self._now_playing.configure_idle_actions(
            on_open_downloads=self._on_open_downloads,
        )
        self._now_playing.cancel_button.setToolTip("Parar download e esvaziar fila (Esc)")
        self._now_playing.skip_button.setToolTip("Pular para o próximo da fila (S)")
        main_column.addWidget(self._now_playing)
        self._activity_panel = ActivityLogPanel(
            on_expanded_changed=self._on_activity_expanded_changed,
        )
        main_column.addWidget(self._activity_panel, stretch=1)

        self._main_host = QWidget()
        self._main_host.setLayout(main_column)

        self._pending_card = Card()
        pending_layout = self._pending_card.body_layout
        pending_header = QHBoxLayout()
        self._pending_title = SectionTitle("Na fila")
        pending_header.addWidget(self._pending_title)
        pending_header.addStretch()
        if self._on_open_downloads is not None:
            dl_link = LinkButton("Downloads")
            dl_link.clicked.connect(self._on_open_downloads)
            pending_header.addWidget(dl_link)
        self._clear_queue_btn = GhostButton("Limpar tudo")
        self._clear_queue_btn.clicked.connect(self._clear_queue_clicked)
        pending_header.addWidget(self._clear_queue_btn)
        pending_layout.addLayout(pending_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._pending_scroll = scroll
        scroll.setMinimumHeight(QUEUE_PENDING_SCROLL_MIN_HEIGHT)
        self._pending_host = QWidget()
        self._pending_layout = QVBoxLayout(self._pending_host)
        self._pending_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._pending_host)
        pending_layout.addWidget(scroll, stretch=1)
        self._empty_widget: Optional[EmptyState] = None

        self._columns_host = QWidget()
        host_layout = QVBoxLayout(self._columns_host)
        host_layout.setContentsMargins(0, 0, 0, 0)

        self._wide_page = QWidget()
        self._wide_layout = QHBoxLayout(self._wide_page)
        apply_layout_spacing(self._wide_layout)

        self._compact_tabs = QTabWidget()
        self._compact_tabs.setObjectName("queueCompactTabs")

        self._mode_stack = QStackedWidget()
        self._mode_stack.addWidget(self._wide_page)
        self._mode_stack.addWidget(self._compact_tabs)
        host_layout.addWidget(self._mode_stack)

        layout.addWidget(self._columns_host, stretch=1)
        self._sync_summary_banner()

    def _bind_shortcuts(self) -> None:
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self._shortcut_escape)
        skip = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        skip.activated.connect(self._shortcut_skip)

    @staticmethod
    def _focus_in_text_input() -> bool:
        focus = QApplication.focusWidget()
        return isinstance(focus, (QLineEdit, QPlainTextEdit))

    def _shortcut_escape(self) -> None:
        if self._focus_in_text_input():
            return
        if self._is_downloading:
            self._on_cancel_download()

    def _shortcut_skip(self) -> None:
        if self._focus_in_text_input():
            return
        if self._is_downloading and len(self._get_queue_snapshot()) > 0:
            self._on_skip_download()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._apply_columns_layout(force=True)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_columns_layout()

    def _detach_from_wide_layout(self) -> None:
        if self._wide_layout is None:
            return
        while self._wide_layout.count():
            item = self._wide_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _detach_from_compact_tabs(self) -> None:
        if self._compact_tabs is None:
            return
        for widget in (self._main_host, self._pending_card):
            index = self._compact_tabs.indexOf(widget)
            if index >= 0:
                self._compact_tabs.removeTab(index)
                widget.setParent(None)

    def _attach_to_wide_layout(self) -> None:
        if self._wide_layout is None:
            return
        if self._wide_layout.indexOf(self._main_host) < 0:
            self._wide_layout.addWidget(self._main_host, LEFT_COLUMN_STRETCH)
        if self._wide_layout.indexOf(self._pending_card) < 0:
            self._wide_layout.addWidget(self._pending_card, RIGHT_COLUMN_STRETCH)

    def _attach_to_compact_tabs(self) -> None:
        if self._compact_tabs is None:
            return
        if self._compact_tabs.indexOf(self._main_host) < 0:
            self._compact_tabs.addTab(self._main_host, "Agora")
        if self._compact_tabs.indexOf(self._pending_card) < 0:
            self._compact_tabs.addTab(self._pending_card, "Na fila")
        self._sync_compact_tab_labels(len(self._get_queue_snapshot()))

    def _apply_columns_layout(self, *, force: bool = False) -> None:
        width = self.width()
        if width <= 0:
            return
        mode = queue_layout_mode(width)
        if not force and mode == self._columns_layout_mode:
            return
        self._columns_layout_mode = mode

        if mode == "columns":
            self._detach_from_compact_tabs()
            self._attach_to_wide_layout()
            if self._mode_stack is not None:
                self._mode_stack.setCurrentWidget(self._wide_page)
        else:
            self._detach_from_wide_layout()
            self._attach_to_compact_tabs()
            if self._mode_stack is not None:
                self._mode_stack.setCurrentWidget(self._compact_tabs)
                self._compact_tabs.setCurrentWidget(self._main_host)

    def _clear_queue_clicked(self) -> None:
        if self._on_clear_queue is not None:
            self._on_clear_queue()

    def activity_log_expanded(self) -> bool:
        return self._activity_panel.is_expanded()

    def apply_activity_settings(self, *, activity_log_expanded: bool) -> None:
        self._activity_panel.set_expanded(activity_log_expanded)

    def append_log(self, message: str) -> None:
        self._activity_panel.append(message)

    def set_activity_clear_enabled(self, enabled: bool) -> None:
        self._activity_panel.set_clear_enabled(enabled)

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
        if percent is not None:
            self._last_percent = percent
        cleaned_url = url.strip()
        if active:
            self._now_playing_url = cleaned_url
            display = (title or "").strip() or truncate_text(url, 48) or "Baixando…"
            meta_lines = []
            if url:
                meta_lines.append(truncate_text(url, QUEUE_URL_TRUNCATE))
            hint = self._pending_position_hint()
            if hint:
                meta_lines.append(hint)
            self._now_playing.set_active(
                title=display,
                meta="\n".join(meta_lines),
                status=status,
                percent=percent,
            )
            if cleaned_url:
                self._apply_now_playing_thumb(cleaned_url)
            if self._columns_layout_mode == "stacked" and self._compact_tabs is not None:
                self._compact_tabs.setCurrentWidget(self._main_host)
        else:
            self._now_playing_url = ""
            self._last_percent = None
            self._now_playing.set_idle()
        self._sync_action_buttons()
        self._sync_summary_banner()

    def apply_progress_event(self, event: ProgressEvent) -> None:
        if event.message and event.event_type in (
            EventType.LOG,
            EventType.DONE,
            EventType.ERROR,
            EventType.CANCELLED,
        ):
            self.append_log(event.message)

        if not self._is_downloading:
            if event.event_type == EventType.ERROR:
                self._activity_panel.set_expanded(True)
            return

        if event.event_type == EventType.PROGRESS:
            if event.percent is not None:
                self._last_percent = event.percent
                self._now_playing.set_percent(event.percent)
            if event.message:
                self._now_playing.set_status(event.message)
            if event.title:
                self._now_playing.set_title(event.title)
        elif event.event_type == EventType.LOG:
            if event.message:
                self._now_playing.set_status(event.message)
                if event.percent is None and "preparando" in event.message.lower():
                    self._now_playing.set_indeterminate(True)
            if event.percent is not None:
                self._last_percent = event.percent
                self._now_playing.set_percent(event.percent)
            if event.title:
                self._now_playing.set_title(event.title)
        elif event.event_type == EventType.DONE:
            self._now_playing.set_percent(1.0)
            if event.message:
                self._now_playing.set_status(event.message)
            if not self._collapsed_activity_after_success:
                self._collapsed_activity_after_success = True
                self._activity_panel.set_expanded(False)
        elif event.event_type == EventType.ERROR:
            if event.message:
                self._now_playing.set_status(event.message)
            self._activity_panel.set_expanded(True)
        elif event.event_type == EventType.CANCELLED:
            self._now_playing.set_status("Cancelando…")
        self._sync_summary_banner()

    def _pending_position_hint(self) -> str:
        pending = len(self._get_queue_snapshot())
        if pending <= 0:
            return ""
        suffix = "vídeo" if pending == 1 else "vídeos"
        return f"{pending} {suffix} na fila após este"

    def _sync_action_buttons(self) -> None:
        pending = len(self._get_queue_snapshot())
        if self._is_downloading:
            self._now_playing.set_cancel_enabled(True)
            self._now_playing.set_skip_enabled(pending > 0, emphasize=pending > 0)
            if self._now_playing_url:
                self._now_playing.set_meta_lines(
                    truncate_text(self._now_playing_url, QUEUE_URL_TRUNCATE),
                    self._pending_position_hint(),
                )
        else:
            self._now_playing.set_cancel_enabled(False)
            self._now_playing.set_skip_enabled(False)

    def _sync_summary_banner(self) -> None:
        pending = len(self._get_queue_snapshot())
        if self._is_downloading:
            parts = ["Download em andamento"]
            if self._last_percent is not None:
                parts.append(f"{int(self._last_percent * 100)}%")
            if pending:
                suffix = "vídeo" if pending == 1 else "vídeos"
                parts.append(f"{pending} {suffix} na fila")
            self._summary_label.setText(" · ".join(parts))
            self._summary_banner.show()
        elif pending:
            suffix = "vídeo" if pending == 1 else "vídeos"
            self._summary_label.setText(
                f"{pending} {suffix} aguardando — use Baixar em Downloads para iniciar."
            )
            self._summary_banner.show()
        else:
            self._summary_banner.hide()

    def _sync_compact_tab_labels(self, pending_count: int) -> None:
        if self._compact_tabs is None:
            return
        idx_main = self._compact_tabs.indexOf(self._main_host)
        idx_pending = self._compact_tabs.indexOf(self._pending_card)
        if idx_main >= 0:
            agora = "Agora ●" if self._is_downloading else "Agora"
            self._compact_tabs.setTabText(idx_main, agora)
        if idx_pending >= 0:
            label = f"Na fila ({pending_count})" if pending_count else "Na fila"
            self._compact_tabs.setTabText(idx_pending, label)

    def _update_header_labels(self, count: int) -> None:
        suffix = f" ({count})" if count else ""
        self._pending_title.setText(f"Na fila{suffix}")
        self._clear_queue_btn.setEnabled(count > 0 and not self._is_downloading)
        self._sync_compact_tab_labels(count)
        self._sync_summary_banner()
        if self._subtitle is not None:
            if self._is_downloading:
                if count:
                    suffix = "vídeo" if count == 1 else "vídeos"
                    self._subtitle.setText(
                        f"Baixando agora · {count} {suffix} aguardando na fila."
                    )
                else:
                    self._subtitle.setText("Baixando agora · fila vazia após este vídeo.")
            elif count:
                suffix = "vídeo" if count == 1 else "vídeos"
                self._subtitle.setText(f"{count} {suffix} aguardando — inicie em Downloads.")
            else:
                self._subtitle.setText(
                    "Acompanhe o download atual, o log e os próximos da fila."
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
            self._pending_scroll.setMinimumHeight(QUEUE_PENDING_SCROLL_MIN_HEIGHT)
            if self._empty_widget is None:
                self._empty_widget = EmptyState(
                    "queue",
                    "Nenhum link na fila",
                    "Use + Fila na tela Downloads para enfileirar vídeos.",
                    cta_label="Ir para Downloads" if self._on_open_downloads else "",
                    on_cta=self._on_open_downloads,
                )
                self._pending_layout.addWidget(self._empty_widget)
            else:
                self._empty_widget.show()
            self._sync_action_buttons()
            return
        self._pending_scroll.setMinimumHeight(QUEUE_PENDING_SCROLL_MIN_HEIGHT_WITH_ITEMS)
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
        icon_on_button(rem, "trash", size=ICON_MD)
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
