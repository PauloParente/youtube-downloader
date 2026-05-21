"""Downloads screen (PySide6)."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Literal, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.config import (
    DEFAULT_DOWNLOADS_DIR,
    QUALITY_COMBO_VALUES,
    QUALITY_DISPLAY_LABELS,
    QUALITY_FROM_DISPLAY,
    QUALITY_OPTIONS,
)
from youtube_downloader.core.download_errors import humanize_ytdlp_error
from youtube_downloader.core.download_job_builder import build_download_job
from youtube_downloader.core.download_url_flow import (
    ResolvedUrlPlanKind,
    format_enqueue_log,
    format_playlist_download_start_log,
    needs_network_expand,
    plan_resolved_urls,
)
from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import VideoPreview, is_youtube_url
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.path_utils import open_path_in_explorer
from youtube_downloader.core.playlist_urls import (
    PlaylistExpandError,
    PlaylistMode,
    UrlKind,
    classify_youtube_url,
    resolve_download_urls,
)
from youtube_downloader.core.preview_cache import PreviewCache
from youtube_downloader.core.settings import AppSettings
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui_qt.downloads_preview import DownloadsPreviewPanel
from youtube_downloader.ui_qt.event_bridge import EventBridge
from youtube_downloader.ui_qt.playlist_choice_dialog import ask_video_in_playlist_choice
from youtube_downloader.ui_qt.icons import icon_on_button, themed_icon
from youtube_downloader.ui_qt.theme import polish_widget
from youtube_downloader.ui_qt.theme_tokens import PAGE_MARGINS
from youtube_downloader.ui_qt.util import pixmap_from_bytes, run_on_main, schedule
from youtube_downloader.ui_qt.widgets.url_drop_line_edit import UrlDropLineEdit
from youtube_downloader.ui_qt.widgets import (
    DownloadOptionsBar,
    DownloadProgressStrip,
    GhostButton,
    IconButton,
    LinkButton,
    PageHeader,
    PrimaryButton,
    SectionTitle,
    apply_page_margins,
    muted_label,
)

logger = get_logger(__name__)

SECTION_GAP = 10
LOG_TEXTBOX_HEIGHT = 160
LOG_TEXTBOX_HEIGHT_COLLAPSED = 48
QUEUE_URL_TRUNCATE = 58
DEFAULT_STATUS_TEXT = "Pronto para baixar."
DOWNLOAD_BTN_LABEL = "Baixar"


class DownloadsView(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        event_bridge: EventBridge,
        preview_cache: PreviewCache,
        on_start_download: Callable[[DownloadJob], None],
        on_cancel_download: Callable[[], None],
        on_persist_settings: Callable[[], None],
        on_record_history: Callable[[ProgressEvent], None],
        on_get_app_settings: Callable[[], AppSettings],
        on_enqueue_url: Callable[[str], bool],
        on_enqueue_urls: Callable[[list[str]], int],
        get_queue_snapshot: Callable[[], list[str]],
        on_remove_queue_at: Callable[[int], None],
        on_clear_queue: Callable[[], None],
        pop_next_queue_url: Callable[[], Optional[str]],
        on_sync_queue_structure: Callable[[], None],
        on_sync_now_playing: Callable[[], None],
        on_open_queue: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._event_bridge = event_bridge
        self._preview_cache = preview_cache
        self._on_start_download = on_start_download
        self._on_cancel_download = on_cancel_download
        self._on_persist_settings = on_persist_settings
        self._on_record_history = on_record_history
        self._get_app_settings = on_get_app_settings
        self._on_enqueue_url = on_enqueue_url
        self._on_enqueue_urls = on_enqueue_urls
        self._get_queue_snapshot = get_queue_snapshot
        self._expanding_playlist = False
        self._stop_batch_on_cancel = False
        self._on_remove_queue_at = on_remove_queue_at
        self._on_clear_queue = on_clear_queue
        self._pop_next_queue_url = pop_next_queue_url
        self._on_sync_queue_structure = on_sync_queue_structure
        self._on_sync_now_playing = on_sync_now_playing
        self._on_open_queue = on_open_queue

        self._is_downloading = False
        self._collapsed_activity_after_success = False
        self._log_lines_since_expand = 0
        self._last_progress_percent: Optional[float] = None
        self._now_playing_title: Optional[str] = None
        self._preview_panel: Optional[DownloadsPreviewPanel] = None
        self._status_reset_after_id: Optional[int] = None
        self._last_download_filepath: Optional[str] = None
        self._log_body: Optional[QWidget] = None
        self._log_expanded = True
        self._build_ui()
        self._bind_shortcuts()

    @property
    def is_downloading(self) -> bool:
        return self._is_downloading

    @property
    def current_url(self) -> str:
        return self._url_entry.text().strip()

    def set_now_playing_title(self, title: str) -> None:
        self._now_playing_title = title.strip() or None

    def collect_settings(self) -> AppSettings:
        return self._collect_settings()

    def apply_settings(self, settings: AppSettings) -> None:
        if settings.quality in QUALITY_OPTIONS:
            self._set_quality_combo(settings.quality)
        self._options_bar.set_audio_only(settings.audio_only)
        self._log_expanded = settings.activity_log_expanded
        self._apply_log_panel_visibility()
        self._update_destination_chip()

    def paste_url(self) -> None:
        self._paste_url()

    def set_download_status(self, text: str) -> None:
        self._set_download_status(text)

    def reset_download_status(self) -> None:
        self._reset_download_status()

    def append_log(self, message: str) -> None:
        self._append_log(message)

    def cancel_download(self) -> None:
        self._cancel_download()

    def skip_to_next_download(self) -> None:
        self._skip_to_next_download()

    def get_cached_preview(self, url: str) -> Optional[VideoPreview]:
        return self._preview_cache.get(url)

    def prefetch_preview_meta(self, url: str) -> None:
        self._preview_cache.request([url])

    def prefetch_preview_meta_many(self, urls: list[str]) -> None:
        self._preview_cache.request(urls)

    def get_now_playing_meta(self) -> dict:
        url = self._url_entry.text().strip()
        cached = self._preview_cache.get(url)
        title = (self._now_playing_title or "").strip()
        if not title and cached and cached.title:
            title = cached.title.strip()
        preview = self._preview_panel.current_preview if self._preview_panel else None
        if not title and preview and preview.title:
            title = preview.title.strip()
        status = DEFAULT_STATUS_TEXT
        if hasattr(self, "_status_label"):
            status = self._status_label.text() or status
        return {
            "active": self._is_downloading,
            "url": url,
            "title": title,
            "status": status,
            "percent": self._last_progress_percent,
            "thumbnail_bytes": (
                cached.thumbnail_bytes if cached and cached.thumbnail_bytes else None
            ),
        }

    def set_url_and_focus(self, url: str) -> None:
        if self._is_downloading:
            return
        self._url_entry.setText(url)
        self._url_entry.setFocus()
        self._schedule_preview_if_ready()

    def show_status_hint(self, text: str, *, reset_after_ms: int = 5000) -> None:
        """Temporary status message (e.g. after pasting URL from history)."""
        if self._is_downloading:
            return
        self._set_download_status(text)
        self._schedule_status_reset(reset_after_ms)

    def should_continue_queue_after_cancel(self) -> bool:
        """True when cancel was Skip (advance queue), not Stop all."""
        return not self._stop_batch_on_cancel and bool(self._get_queue_snapshot())

    def start_download_for_url(self, url: str) -> None:
        cleaned = url.strip()
        if not cleaned:
            return
        self._url_entry.setText(cleaned)
        self._schedule_preview_if_ready()
        self._run_download_job_for_url(cleaned)

    def continue_queue_for_url(self, url: str) -> None:
        """Start next queued item without heavy UI reset (batch advance)."""
        cleaned = url.strip()
        if not cleaned:
            return
        self._url_entry.setText(cleaned)
        self._now_playing_title = None
        cached = self._preview_cache.get(cleaned)
        if cached and cached.title:
            self._now_playing_title = cached.title.strip()
        self._run_download_job_for_url(cleaned, queue_continue=True)

    def _schedule_preview_if_ready(self) -> None:
        if self._preview_panel is not None:
            self._preview_panel.schedule_preview()

    def force_release_download_ui(self) -> None:
        """Recover when the worker finished but a terminal UI event was missed."""
        if not self._is_downloading:
            return
        logger.warning("Recuperando UI de download (evento terminal ausente)")
        self._release_download_ui()

    def _get_quality_internal(self) -> str:
        display = self._options_bar.quality_combo.currentText()
        return QUALITY_FROM_DISPLAY.get(display, QUALITY_OPTIONS[0])

    def _set_quality_combo(self, quality: str) -> None:
        label = QUALITY_DISPLAY_LABELS.get(quality, QUALITY_DISPLAY_LABELS[QUALITY_OPTIONS[0]])
        self._options_bar.quality_combo.setCurrentText(label)

    def _on_url_dropped(self, url: str) -> None:
        self._url_entry.setText(url)
        self._on_url_changed()

    def _on_url_changed(self) -> None:
        if self._preview_panel is not None:
            self._preview_panel.hide_alert()
        self._update_url_clear_visibility()
        self._sync_url_validation_icons()
        self._sync_download_button()
        self._schedule_preview_if_ready()

    def _sync_url_validation_icons(self) -> None:
        if not hasattr(self, "_url_valid_icon"):
            return
        url = self._url_entry.text().strip()
        if not url:
            self._url_valid_icon.hide()
            self._url_invalid_icon.hide()
        elif is_youtube_url(url):
            self._url_valid_icon.show()
            self._url_invalid_icon.hide()
        else:
            self._url_valid_icon.hide()
            self._url_invalid_icon.show()

    def _update_progress_percent(self, percent: Optional[float]) -> None:
        self._last_progress_percent = percent
        if hasattr(self, "_progress_strip"):
            self._progress_strip.set_percent(percent)

    def _toggle_log_panel(self) -> None:
        if self._log_body is None:
            return
        self._log_expanded = not self._log_expanded
        self._apply_log_panel_visibility()
        if self._log_expanded:
            self._log_lines_since_expand = 0
            self._update_activity_badge()
        self._persist_activity_log_state()

    def _apply_log_panel_visibility(self) -> None:
        if self._log_body is None:
            return
        self._log_body.setVisible(True)
        height = LOG_TEXTBOX_HEIGHT if self._log_expanded else LOG_TEXTBOX_HEIGHT_COLLAPSED
        self._log_box.setFixedHeight(height)
        icon_on_button(self._log_toggle_btn, "chevron", size=14)

    def _persist_activity_log_state(self) -> None:
        self._on_persist_settings()

    def _update_activity_badge(self) -> None:
        if not hasattr(self, "_activity_badge"):
            return
        if self._log_expanded or self._log_lines_since_expand <= 0:
            self._activity_badge.hide()
        else:
            self._activity_badge.setText(str(self._log_lines_since_expand))
            self._activity_badge.show()

    def _update_enqueue_label(self) -> None:
        count = len(self._get_queue_snapshot())
        self._enqueue_btn.setText(f"+ Fila ({count})" if count else "+ Fila")
        if hasattr(self, "_view_queue_btn"):
            if count and self._on_open_queue is not None:
                self._view_queue_btn.setText(f"Ver fila ({count})")
                self._view_queue_btn.show()
            else:
                self._view_queue_btn.hide()

    def _update_url_clear_visibility(self) -> None:
        has_text = bool(self._url_entry.text().strip())
        self._clear_url_btn.setVisible(has_text)

    def _sync_download_button(self) -> None:
        url = self._url_entry.text().strip()
        ready = bool(url and is_youtube_url(url)) or (
            not url and self._has_pending_queue()
        )
        if self._expanding_playlist:
            self._download_btn.setText("A preparar…")
            self._download_btn.setEnabled(False)
            self._download_btn.setToolTip("")
            self._download_btn.setObjectName("primaryOutline")
            self._download_btn.setCursor(Qt.CursorShape.WaitCursor)
        elif self._is_downloading:
            self._download_btn.setText(DOWNLOAD_BTN_LABEL)
            self._download_btn.hide()
            self._download_btn.setEnabled(False)
        else:
            self._download_btn.show()
            self._download_btn.setText(DOWNLOAD_BTN_LABEL)
            self._download_btn.setCursor(Qt.CursorShape.ArrowCursor)
            self._download_btn.setEnabled(ready)
            if ready:
                self._download_btn.setObjectName("primary")
                self._download_btn.setToolTip("")
            else:
                self._download_btn.setObjectName("primaryOutline")
                self._download_btn.setToolTip("Cole um link do YouTube válido")
        polish_widget(self._download_btn)

    def _sync_progress_context(self) -> None:
        title = self._now_playing_title or ""
        if not title:
            preview = self._current_preview()
            if preview and preview.title:
                title = preview.title
        if not title:
            url = self._url_entry.text().strip()
            title = truncate_text(url, 50) if url else "Baixando…"
        url = self._url_entry.text().strip()
        thumb = None
        if url:
            cached = self._preview_cache.get(url)
            if cached and cached.thumbnail_bytes:
                thumb = pixmap_from_bytes(cached.thumbnail_bytes, (64, 36))
        self._progress_strip.set_context(title, thumb)

    def _sync_progress_indeterminate(self, status_text: str = "") -> None:
        text = status_text or (
            self._status_label.text() if hasattr(self, "_status_label") else ""
        )
        busy = self._expanding_playlist or any(
            k in text.casefold()
            for k in ("playlist", "preparando", "obter vídeos", "pulando")
        )
        self._progress_strip.set_indeterminate(busy)

    def _sync_progress_strip(self) -> None:
        active = self._is_downloading or self._expanding_playlist
        self._progress_strip.set_active(active)
        if active:
            self._sync_progress_context()
            self._sync_progress_indeterminate()
            self._cancel_btn.hide()
        else:
            self._progress_strip.set_indeterminate(False)
            self._progress_strip.set_percent(0)
            self._sync_action_buttons()
            self._sync_download_button()

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self._shortcut_start)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, self._shortcut_start)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self._shortcut_escape)

    def _shortcut_start(self) -> None:
        if self._is_downloading or self._expanding_playlist:
            return
        focus = QApplication.focusWidget()
        if focus is self._options_bar.quality_combo:
            return
        if self._download_btn.isEnabled() and self._download_btn.isVisible():
            self._start_download()

    def _shortcut_escape(self) -> None:
        if self._is_downloading:
            self._cancel_download()
        else:
            self._clear_url()

    def _update_destination_chip(self) -> None:
        if not hasattr(self, "_destination_chip"):
            return
        path = self._output_dir()
        name = os.path.basename(path.rstrip("\\/")) or path
        display = truncate_text(path, 42) if len(path) > 42 else path
        self._destination_chip.setText(f"Pasta: {name}")
        self._destination_chip.setToolTip(path)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        apply_page_margins(scroll_layout)

        scroll_layout.addWidget(
            PageHeader(
                "Downloads",
                "Cole um link, visualize o preview e inicie o download.",
            )
        )

        self._url_entry = UrlDropLineEdit(self._on_url_dropped)
        self._url_entry.setObjectName("urlHero")
        self._url_entry.setPlaceholderText("Cole ou arraste um link do YouTube")
        link_action = QAction(themed_icon("link", 18), "")
        self._url_entry.addAction(link_action, QLineEdit.ActionPosition.LeadingPosition)
        self._url_entry.textChanged.connect(self._on_url_changed)
        self._preview_panel = DownloadsPreviewPanel(
            self,
            get_url=lambda: self._url_entry.text(),
            event_bridge=self._event_bridge,
            preview_cache=self._preview_cache,
            is_downloading=lambda: self._is_downloading,
            on_open_queue=self._on_open_queue,
        )

        url_tool_row = QFrame()
        url_tool_row.setObjectName("urlToolRow")
        url_row = QHBoxLayout(url_tool_row)
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.setSpacing(8)
        url_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        url_row.addWidget(self._url_entry, stretch=1)
        self._url_valid_icon = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._url_valid_icon.setObjectName("urlValidIcon")
        self._url_valid_icon.setPixmap(themed_icon("link", 18).pixmap(18, 18))
        self._url_valid_icon.hide()
        url_row.addWidget(self._url_valid_icon)
        self._url_invalid_icon = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._url_invalid_icon.setObjectName("urlInvalidIcon")
        self._url_invalid_icon.setPixmap(themed_icon("clear", 18).pixmap(18, 18))
        self._url_invalid_icon.hide()
        url_row.addWidget(self._url_invalid_icon)
        paste_btn = GhostButton("Colar")
        icon_on_button(paste_btn, "link", size=16)
        paste_btn.clicked.connect(self._paste_url)
        url_row.addWidget(paste_btn)
        self._enqueue_btn = GhostButton("+ Fila")
        icon_on_button(self._enqueue_btn, "queue", size=16)
        self._enqueue_btn.clicked.connect(self._enqueue_current_url)
        url_row.addWidget(self._enqueue_btn)
        self._view_queue_btn = LinkButton("")
        self._view_queue_btn.hide()
        if self._on_open_queue is not None:
            self._view_queue_btn.clicked.connect(self._on_open_queue)
        url_row.addWidget(self._view_queue_btn)
        self._clear_url_btn = IconButton(tooltip="Limpar URL")
        icon_on_button(self._clear_url_btn, "clear", size=16)
        self._clear_url_btn.clicked.connect(self._clear_url)
        self._clear_url_btn.hide()
        url_row.addWidget(self._clear_url_btn)
        scroll_layout.addWidget(url_tool_row)

        self._options_bar = DownloadOptionsBar(on_changed=self._on_options_changed)
        self._set_quality_combo(QUALITY_OPTIONS[0])
        self._preview_panel.attach_to(scroll_layout, options_bar=self._options_bar)

        self._progress_strip = DownloadProgressStrip(on_cancel=self._cancel_download)
        scroll_layout.addWidget(self._progress_strip)

        log_header = QHBoxLayout()
        self._log_toggle_btn = QPushButton()
        self._log_toggle_btn.setObjectName("sectionToggle")
        icon_on_button(self._log_toggle_btn, "chevron", size=14)
        self._log_toggle_btn.clicked.connect(self._toggle_log_panel)
        log_header.addWidget(self._log_toggle_btn)
        log_header.addWidget(SectionTitle("Atividade"))
        self._activity_badge = QLabel("0")
        self._activity_badge.setObjectName("durationBadge")
        self._activity_badge.hide()
        log_header.addWidget(self._activity_badge)
        log_header.addStretch()
        self._clear_log_btn = QPushButton("Limpar")
        self._clear_log_btn.clicked.connect(self._clear_log)
        log_header.addWidget(self._clear_log_btn)
        scroll_layout.addLayout(log_header)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_card_layout = QVBoxLayout(log_card)
        self._log_body = QWidget()
        log_body_layout = QVBoxLayout(self._log_body)
        self._log_box = QPlainTextEdit()
        self._log_box.setObjectName("logInset")
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(LOG_TEXTBOX_HEIGHT)
        log_body_layout.addWidget(self._log_box)
        log_card_layout.addWidget(self._log_body)
        scroll_layout.addWidget(log_card)

        scroll.setWidget(scroll_content)
        root.addWidget(scroll, stretch=1)

        self._action_dock = QFrame()
        self._action_dock.setObjectName("actionDock")
        dock_l, dock_t, dock_r, dock_b = PAGE_MARGINS
        dock_layout = QVBoxLayout(self._action_dock)
        dock_layout.setContentsMargins(dock_l, 12, dock_r, dock_b)
        dock_layout.setSpacing(10)

        self._status_label = muted_label(DEFAULT_STATUS_TEXT)
        dock_layout.addWidget(self._status_label)

        self._shortcuts_hint = muted_label("Ctrl+V colar · Enter baixar · Esc cancelar ou limpar")
        dock_layout.addWidget(self._shortcuts_hint)

        btn_row = QHBoxLayout()
        self._destination_chip = QPushButton()
        self._destination_chip.setObjectName("destinationChip")
        self._destination_chip.setFlat(True)
        self._destination_chip.setCursor(Qt.CursorShape.PointingHandCursor)
        self._destination_chip.clicked.connect(self._open_folder)
        self._update_destination_chip()
        btn_row.addWidget(self._destination_chip)
        self._open_folder_btn = QPushButton("Abrir pasta")
        icon_on_button(self._open_folder_btn, "folder", size=18)
        self._open_folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self._open_folder_btn)
        self._open_file_btn = QPushButton("Abrir arquivo")
        icon_on_button(self._open_file_btn, "file", size=18)
        self._open_file_btn.setEnabled(False)
        self._open_file_btn.clicked.connect(self._open_last_file)
        btn_row.addWidget(self._open_file_btn)
        self._cancel_btn = GhostButton("Limpar URL")
        icon_on_button(self._cancel_btn, "clear", size=16)
        self._cancel_btn.clicked.connect(self._clear_url)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        self._download_btn = PrimaryButton("Baixar")
        icon_on_button(self._download_btn, "download", size=18)
        self._download_btn.setMinimumWidth(140)
        self._download_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._download_btn)
        dock_layout.addLayout(btn_row)

        root.addWidget(self._action_dock)

        self._log_expanded = self._get_app_settings().activity_log_expanded
        self._apply_log_panel_visibility()
        self._on_url_changed()
        self._sync_action_buttons()
        self._sync_download_button()
        self._update_enqueue_label()

    def _output_dir(self) -> str:
        path = self._get_app_settings().output_dir.strip()
        return path or str(DEFAULT_DOWNLOADS_DIR)

    def _collect_settings(self) -> AppSettings:
        app = self._get_app_settings()
        return AppSettings(
            output_dir=app.output_dir,
            quality=self._get_quality_internal(),
            audio_only=self._options_bar.is_audio_only(),
            language=app.language,
            video_format=app.video_format,
            export_profile=app.export_profile,
            audio_bitrate=app.audio_bitrate,
            bandwidth_limit_kbps=app.bandwidth_limit_kbps,
            notify_on_complete=app.notify_on_complete,
            auto_download_subtitles=app.auto_download_subtitles,
            appearance_mode=app.appearance_mode,
            cookies_file=app.cookies_file,
            activity_log_expanded=self._log_expanded,
        )

    def _on_options_changed(self) -> None:
        self._on_persist_settings()

    def _on_quality_changed(self, _choice: str) -> None:
        self._on_persist_settings()

    def _paste_url(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self._url_entry.setText(text)
            self._schedule_preview_if_ready()

    def _clear_url(self) -> None:
        self._url_entry.clear()
        if not self._is_downloading and self._preview_panel is not None:
            self._preview_panel.clear()

    def _clear_log(self) -> None:
        self._log_box.clear()

    def _set_expand_busy(self, busy: bool) -> None:
        self._expanding_playlist = busy
        if busy:
            self._set_download_status("A obter vídeos da playlist…")
            self._status_reset_after_id = None
        elif not self._is_downloading:
            self._schedule_status_reset()
        self._sync_progress_strip()
        self._sync_download_button()
        if self._is_downloading:
            return
        self._enqueue_btn.setEnabled(not busy)

    def _resolve_urls_async(
        self,
        url: str,
        playlist_mode: Optional[PlaylistMode],
        on_done: Callable[[Optional[list[str]], Optional[str]], None],
    ) -> None:
        def worker() -> None:
            try:
                urls = resolve_download_urls(url, playlist_mode=playlist_mode)
                run_on_main(self, lambda: on_done(urls, None))
            except PlaylistExpandError as exc:
                run_on_main(self, lambda: on_done(None, str(exc)))
            except Exception as exc:
                logger.exception("Falha ao resolver URLs: %s", url[:80])
                run_on_main(self, lambda: on_done(None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _resolve_and_act(
        self,
        url: str,
        *,
        action: Literal["download", "enqueue"],
    ) -> None:
        if self._expanding_playlist:
            return
        cleaned = url.strip()
        if not cleaned or not is_youtube_url(cleaned):
            self._append_log("Informe uma URL válida do YouTube.")
            return

        kind = classify_youtube_url(cleaned)
        playlist_mode: Optional[PlaylistMode] = None
        if kind == UrlKind.VIDEO_IN_PLAYLIST:
            preview = self._preview_panel.current_preview if self._preview_panel else None
            count = (
                preview.playlist_count
                if preview and preview.is_playlist
                else None
            )
            playlist_mode = ask_video_in_playlist_choice(
                self.window(),
                playlist_count=count,
            )
            if playlist_mode is None:
                return

        if needs_network_expand(kind, playlist_mode):

            def on_done(urls: Optional[list[str]], error: Optional[str]) -> None:
                self._set_expand_busy(False)
                if error or not urls:
                    self._append_log(
                        f"Erro ao obter vídeos da playlist: {error or 'lista vazia'}"
                    )
                    return
                self._on_urls_resolved(urls, action=action)

            self._set_expand_busy(True)
            self._resolve_urls_async(cleaned, playlist_mode, on_done)
            return

        try:
            urls = resolve_download_urls(cleaned, playlist_mode=playlist_mode)
        except (PlaylistExpandError, ValueError) as exc:
            self._append_log(f"Erro: {exc}")
            return
        self._on_urls_resolved(urls, action=action)

    def _log_enqueue_result(self, added: int, total: int) -> None:
        self._append_log(format_enqueue_log(added, total))

    def _on_urls_resolved(
        self,
        urls: list[str],
        *,
        action: Literal["download", "enqueue"],
    ) -> None:
        plan = plan_resolved_urls(urls, action, is_downloading=self._is_downloading)
        if plan.kind == ResolvedUrlPlanKind.NO_VIDEOS:
            self._append_log("Nenhum vídeo encontrado para enfileirar.")
            return

        if plan.kind == ResolvedUrlPlanKind.ENQUEUE_ALL:
            to_enqueue = plan.urls_to_enqueue
            added = self._on_enqueue_urls(to_enqueue)
            self._log_enqueue_result(added, len(to_enqueue))
            self._sync_queue_ui()
            return

        if plan.kind == ResolvedUrlPlanKind.START_SINGLE:
            self._run_download_job_for_url(plan.start_url)
            return

        rest = plan.urls_to_enqueue
        if rest:
            added_rest = self._on_enqueue_urls(rest)
            skipped = len(rest) - added_rest
            self._append_log(
                format_playlist_download_start_log(
                    len(urls), added_rest=added_rest, skipped=skipped
                )
            )
        else:
            self._append_log(format_playlist_download_start_log(1, added_rest=0, skipped=0))

        first = plan.start_url
        self._url_entry.setText(first)
        self._schedule_preview_if_ready()
        self._append_log(
            f"Iniciando: {truncate_text(first, QUEUE_URL_TRUNCATE)}"
        )
        self._run_download_job_for_url(first)

    def _update_open_file_button(self) -> None:
        enabled = bool(
            self._last_download_filepath
            and os.path.isfile(self._last_download_filepath)
        )
        self._open_file_btn.setEnabled(enabled)

    def _open_last_file(self) -> None:
        if self._last_download_filepath and os.path.isfile(self._last_download_filepath):
            self._open_path_in_explorer(self._last_download_filepath)

    def _enqueue_current_url(self) -> None:
        if self._is_downloading and self._expanding_playlist:
            return
        url = self._url_entry.text().strip()
        self._resolve_and_act(url, action="enqueue")

    def _open_path_in_explorer(self, path: str) -> None:
        try:
            open_path_in_explorer(path)
        except OSError as exc:
            logger.exception("Falha ao abrir pasta: %s", path)
            self._append_log(f"Erro ao abrir pasta: {exc}")

    def _open_folder(self) -> None:
        output_dir = self._output_dir()
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as exc:
                self._append_log(f"Erro ao criar pasta: {exc}")
                return
        self._open_path_in_explorer(output_dir)

    def _append_log(self, message: str) -> None:
        self._log_box.appendPlainText(message)
        self._log_box.verticalScrollBar().setValue(
            self._log_box.verticalScrollBar().maximum()
        )
        if not self._log_expanded:
            self._log_lines_since_expand += 1
            self._update_activity_badge()

    def _set_download_status(self, text: str) -> None:
        self._status_label.setText(text)
        if self._is_downloading or self._expanding_playlist:
            self._progress_strip.set_message(text)
            self._sync_progress_indeterminate(text)

    def _reset_download_status(self) -> None:
        self._status_reset_after_id = None
        self._set_download_status(DEFAULT_STATUS_TEXT)

    def _schedule_status_reset(self, delay_ms: int = 3000) -> None:
        schedule(self, delay_ms, self._reset_download_status)

    def _current_preview(self) -> Optional[VideoPreview]:
        if self._preview_panel is None:
            return None
        return self._preview_panel.current_preview

    def _get_preview_title_for_log(self) -> Optional[str]:
        preview = self._current_preview()
        if preview and preview.title:
            return preview.title.strip()
        title_lbl = (
            self._preview_panel.preview_title_label if self._preview_panel else None
        )
        if title_lbl is not None:
            title = title_lbl.text().strip()
            if title and title not in (
                "Carregando preview…",
                "—",
                "Preview indisponível",
            ):
                return title
        return None

    def _get_preview_channel_name(self) -> str:
        preview = self._current_preview()
        if preview and preview.uploader:
            return preview.uploader.strip()
        return ""

    def _get_preview_channel_url(self) -> str:
        preview = self._current_preview()
        if preview and preview.channel_url:
            return preview.channel_url.strip()
        return ""

    def _get_preview_thumbnail_bytes(self) -> Optional[bytes]:
        preview = self._current_preview()
        if preview and preview.thumbnail_bytes:
            return preview.thumbnail_bytes
        return None

    def _prefetch_history_meta(self, url: str) -> None:
        """Fetch per-video title/thumbnail for history and queue cards."""
        self._preview_cache.request([url])

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._clear_url_btn.setEnabled(True)
        self._url_entry.setEnabled(True)
        self._clear_log_btn.setEnabled(enabled)
        self._open_folder_btn.setEnabled(enabled)
        if not enabled:
            self._open_file_btn.setEnabled(False)
        else:
            self._update_open_file_button()
        self._options_bar.set_enabled(enabled)
        self._enqueue_btn.setEnabled(enabled)
        self._download_btn.setEnabled(enabled)
        self._sync_action_buttons()
        self._sync_progress_strip()
        self._sync_download_button()

    def _has_pending_queue(self) -> bool:
        return bool(self._get_queue_snapshot())

    def _sync_action_buttons(self) -> None:
        if self._is_downloading:
            self._cancel_btn.hide()
        else:
            self._cancel_btn.show()
            self._cancel_btn.setText("Limpar URL")
            try:
                self._cancel_btn.clicked.disconnect()
            except RuntimeError:
                pass
            self._cancel_btn.clicked.connect(self._clear_url)

    def _between_queue_items_ui(self) -> None:
        """Keep batch controls while the next queued item is about to start."""
        self._is_downloading = True
        self._last_progress_percent = 0.0
        self._set_download_status("Preparando próximo da fila…")
        self._sync_action_buttons()
        self._sync_progress_strip()
        self._on_sync_now_playing()

    def _release_download_ui(self) -> None:
        self._is_downloading = False
        self._stop_batch_on_cancel = False
        self._last_progress_percent = None
        self._now_playing_title = None
        self._set_controls_enabled(True)
        self._schedule_status_reset()
        self._sync_queue_ui()
        self._sync_progress_strip()
        self._sync_download_button()

    def _start_download(self) -> None:
        if self._is_downloading or self._expanding_playlist:
            return

        url = self._url_entry.text().strip()
        if not url:
            url = (self._pop_next_queue_url() or "").strip()
            if url:
                self._url_entry.setText(url)
                self._schedule_preview_if_ready()
                self._append_log(
                    f"Iniciando da fila: {truncate_text(url, QUEUE_URL_TRUNCATE)}"
                )
                self._run_download_job_for_url(url)
            else:
                logger.warning("Download bloqueado: URL vazia e fila vazia")
                self._append_log(
                    "Erro: informe a URL do vídeo ou adicione links à fila."
                )
            return

        self._resolve_and_act(url, action="download")

    def _run_download_job_for_url(self, url: str, *, queue_continue: bool = False) -> None:
        cleaned = url.strip()
        if not cleaned:
            return

        output_dir = self._output_dir()
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as exc:
                logger.error("Download bloqueado: pasta invalida %s (%s)", output_dir, exc)
                self._append_log(f"Erro: não foi possível criar a pasta de destino: {exc}")
                return

        job = build_download_job(
            url=cleaned,
            output_dir=output_dir,
            quality=self._get_quality_internal(),
            audio_only=self._options_bar.is_audio_only(),
            preferences=self._get_app_settings(),
        )
        if not queue_continue:
            self._on_persist_settings()
        if not self._preview_cache.get(cleaned):
            self._prefetch_history_meta(cleaned)

        self._is_downloading = True
        if self._preview_panel is not None:
            self._preview_panel.cancel_pending_schedule()
        if not queue_continue:
            self._set_controls_enabled(False)
        self._last_progress_percent = 0.0
        self._status_reset_after_id = None
        start_label = self._get_preview_title_for_log() or truncate_text(cleaned, 60)
        self._append_log(f"Iniciando download: {start_label}")
        self._set_download_status("Baixando…")
        self._sync_progress_context()
        self._sync_action_buttons()
        self._sync_progress_strip()
        if self._preview_panel is not None:
            self._preview_panel.hide_alert()
        self._sync_queue_ui()
        self._on_sync_now_playing()

        self._on_start_download(job)

    def _sync_queue_ui(self) -> None:
        self._update_enqueue_label()
        self._on_sync_queue_structure()

    def _cancel_download(self) -> None:
        if not self._is_downloading:
            self._clear_url()
            return
        self._stop_batch_on_cancel = True
        pending = len(self._get_queue_snapshot())
        logger.info(
            "Usuario cancelou downloads (fila=%d): %s",
            pending,
            self._url_entry.text().strip(),
        )
        self._on_cancel_download()
        if pending:
            self._on_clear_queue()
            self._append_log("Cancelando download e fila pendente…")
        else:
            self._append_log("Cancelando download…")
        self._set_download_status("Cancelando…")

    def _skip_to_next_download(self) -> None:
        if not self._is_downloading:
            return
        if not self._has_pending_queue():
            return
        self._stop_batch_on_cancel = False
        logger.info(
            "Usuario pulou para proximo da fila: %s",
            self._url_entry.text().strip(),
        )
        self._on_cancel_download()
        self._set_download_status("Pulando para o próximo…")
        self._append_log("Pulando para o próximo da fila…")

    def handle_progress_event(self, event: ProgressEvent) -> None:
        if self._preview_panel is not None and self._preview_panel.handle_progress_event(
            event
        ):
            return

        if event.title:
            self._now_playing_title = event.title.strip()

        if event.event_type == EventType.PROGRESS:
            if event.percent is not None:
                self._update_progress_percent(event.percent)
            if event.message:
                self._set_download_status(event.message)

        elif event.event_type == EventType.LOG:
            self._append_log(event.message)
            if event.percent is not None:
                self._update_progress_percent(event.percent)
            self._set_download_status(event.message)

        elif event.event_type in (
            EventType.DONE,
            EventType.ERROR,
            EventType.CANCELLED,
        ):
            try:
                if event.percent is not None:
                    self._update_progress_percent(event.percent)
                elif event.event_type == EventType.DONE:
                    self._update_progress_percent(1.0)
                self._append_log(event.message)
                if event.event_type == EventType.DONE:
                    if not self._collapsed_activity_after_success:
                        self._collapsed_activity_after_success = True
                        self._log_expanded = False
                        self._apply_log_panel_visibility()
                        self._on_persist_settings()
                    if self._preview_panel is not None:
                        self._preview_panel.hide_alert()
                    if self._has_pending_queue():
                        self._set_download_status("Vídeo concluído — próximo da fila…")
                    else:
                        self._set_download_status("Download concluído.")
                    if event.filepath and os.path.isfile(event.filepath):
                        self._last_download_filepath = event.filepath
                        self._update_open_file_button()
                        try:
                            self._on_record_history(event)
                        except Exception:
                            logger.exception("Falha ao registrar download no historico")
                    self._url_entry.setFocus()
                elif event.event_type == EventType.ERROR:
                    friendly = humanize_ytdlp_error(event.message)
                    self._set_download_status(friendly)
                    if self._preview_panel is not None:
                        self._preview_panel.show_alert(friendly)
                else:
                    self._set_download_status("Download cancelado.")
            finally:
                advance_after = (
                    event.event_type in (EventType.DONE, EventType.CANCELLED)
                    and self._has_pending_queue()
                    and not self._stop_batch_on_cancel
                )
                if advance_after:
                    self._between_queue_items_ui()
                else:
                    self._release_download_ui()
