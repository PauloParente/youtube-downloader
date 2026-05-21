"""Downloads screen (PySide6)."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Literal, Optional

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
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
from youtube_downloader.ui_qt.util import run_on_main, schedule

logger = get_logger(__name__)

SECTION_GAP = 10
LOG_TEXTBOX_HEIGHT = 160
QUEUE_URL_TRUNCATE = 58
DEFAULT_STATUS_TEXT = "Pronto para baixar."


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

        self._is_downloading = False
        self._last_progress_percent: Optional[float] = None
        self._now_playing_title: Optional[str] = None
        self._preview_panel: Optional[DownloadsPreviewPanel] = None
        self._status_reset_after_id: Optional[int] = None
        self._last_download_filepath: Optional[str] = None
        self._log_body: Optional[QWidget] = None
        self._log_expanded = True
        self._build_ui()

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
        self._audio_only_var.setChecked(settings.audio_only)
        self._on_audio_toggle()

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
        display = self._quality_combo.currentText()
        return QUALITY_FROM_DISPLAY.get(display, QUALITY_OPTIONS[0])

    def _set_quality_combo(self, quality: str) -> None:
        label = QUALITY_DISPLAY_LABELS.get(quality, QUALITY_DISPLAY_LABELS[QUALITY_OPTIONS[0]])
        self._quality_combo.setCurrentText(label)

    def _update_progress_percent(self, percent: Optional[float]) -> None:
        self._last_progress_percent = percent

    def _toggle_log_panel(self) -> None:
        if self._log_body is None:
            return
        self._log_expanded = not self._log_expanded
        self._log_body.setVisible(self._log_expanded)
        self._log_toggle_btn.setText("▼" if self._log_expanded else "▶")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        scroll_layout.addWidget(QLabel("URL do YouTube"))
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("🔗"))
        self._url_entry = QLineEdit()
        self._url_entry.setPlaceholderText("Cole o link do vídeo ou playlist aqui...")
        self._url_entry.textChanged.connect(lambda _: self._schedule_preview_if_ready())
        url_row.addWidget(self._url_entry, stretch=1)
        self._preview_panel = DownloadsPreviewPanel(
            self,
            get_url=lambda: self._url_entry.text(),
            event_bridge=self._event_bridge,
            preview_cache=self._preview_cache,
            is_downloading=lambda: self._is_downloading,
        )
        self._clear_url_btn = QPushButton("✕")
        self._clear_url_btn.clicked.connect(self._clear_url)
        url_row.addWidget(self._clear_url_btn)
        self._enqueue_btn = QPushButton("+ Fila")
        self._enqueue_btn.clicked.connect(self._enqueue_current_url)
        url_row.addWidget(self._enqueue_btn)
        scroll_layout.addLayout(url_row)

        mid = QWidget()
        mid_layout = QVBoxLayout(mid)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        preview_card = self._preview_panel.build_into(mid)
        opts = QVBoxLayout(preview_card)
        self._audio_only_var = QCheckBox("Somente áudio")
        self._audio_only_var.toggled.connect(lambda _: self._on_options_changed())
        opts.addWidget(self._audio_only_var)
        opts.addWidget(QLabel("Qualidade"))
        self._quality_combo = QComboBox()
        self._quality_combo.addItems(QUALITY_COMBO_VALUES)
        self._quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self._set_quality_combo(QUALITY_OPTIONS[0])
        opts.addWidget(self._quality_combo)
        scroll_layout.addWidget(mid)

        log_header = QHBoxLayout()
        self._log_toggle_btn = QPushButton("▼")
        self._log_toggle_btn.clicked.connect(self._toggle_log_panel)
        log_header.addWidget(self._log_toggle_btn)
        log_header.addWidget(QLabel("<b>ATIVIDADE</b>"))
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
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(LOG_TEXTBOX_HEIGHT)
        log_body_layout.addWidget(self._log_box)
        log_card_layout.addWidget(self._log_body)
        scroll_layout.addWidget(log_card)

        scroll.setWidget(scroll_content)
        root.addWidget(scroll, stretch=1)

        self._status_label = QLabel(DEFAULT_STATUS_TEXT)
        root.addWidget(self._status_label)
        btn_row = QHBoxLayout()
        self._open_folder_btn = QPushButton("📁  Abrir pasta")
        self._open_folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self._open_folder_btn)
        self._open_file_btn = QPushButton("📄  Abrir arquivo")
        self._open_file_btn.setEnabled(False)
        self._open_file_btn.clicked.connect(self._open_last_file)
        btn_row.addWidget(self._open_file_btn)
        self._cancel_btn = QPushButton("✕  Cancelar")
        self._cancel_btn.clicked.connect(self._cancel_download)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        self._download_btn = QPushButton("⬇  Baixar")
        self._download_btn.setObjectName("primary")
        self._download_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._download_btn)
        root.addLayout(btn_row)
        self._sync_action_buttons()
        self._on_sync_queue_structure()

    def _output_dir(self) -> str:
        path = self._get_app_settings().output_dir.strip()
        return path or str(DEFAULT_DOWNLOADS_DIR)

    def _collect_settings(self) -> AppSettings:
        app = self._get_app_settings()
        return AppSettings(
            output_dir=app.output_dir,
            quality=self._get_quality_internal(),
            audio_only=self._audio_only_var.isChecked(),
        )

    def _on_options_changed(self) -> None:
        self._on_audio_toggle()
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
        if self._is_downloading:
            return
        self._download_btn.setEnabled(not busy)
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

    def _on_audio_toggle(self) -> None:
        self._quality_combo.setEnabled(not self._audio_only_var.isChecked())

    def _append_log(self, message: str) -> None:
        self._log_box.appendPlainText(message)
        self._log_box.verticalScrollBar().setValue(
            self._log_box.verticalScrollBar().maximum()
        )

    def _set_download_status(self, text: str) -> None:
        self._status_label.setText(text)

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
        self._audio_only_var.setEnabled(enabled)
        self._enqueue_btn.setEnabled(enabled)
        if enabled:
            self._on_audio_toggle()
        else:
            self._quality_combo.setEnabled(False)
        self._download_btn.setEnabled(enabled)
        self._sync_action_buttons()

    def _has_pending_queue(self) -> bool:
        return bool(self._get_queue_snapshot())

    def _sync_action_buttons(self) -> None:
        if self._is_downloading:
            self._cancel_btn.setText("✕  Cancelar")
            try:
                self._cancel_btn.clicked.disconnect()
            except RuntimeError:
                pass
            self._cancel_btn.clicked.connect(self._cancel_download)
        else:
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
        self._on_sync_now_playing()

    def _release_download_ui(self) -> None:
        self._is_downloading = False
        self._stop_batch_on_cancel = False
        self._last_progress_percent = None
        self._now_playing_title = None
        self._set_controls_enabled(True)
        self._schedule_status_reset()
        self._on_sync_queue_structure()

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
            audio_only=self._audio_only_var.isChecked(),
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
        self._sync_action_buttons()
        if queue_continue:
            self._on_sync_now_playing()
        else:
            self._on_sync_queue_structure()

        self._on_start_download(job)

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
                    if self._has_pending_queue():
                        self._set_download_status("Vídeo concluído — próximo da fila…")
                    else:
                        self._set_download_status(
                            "Download concluído. Use Limpar URL ou cole outro link."
                        )
                    if event.filepath and os.path.isfile(event.filepath):
                        self._last_download_filepath = event.filepath
                        self._update_open_file_button()
                        try:
                            self._on_record_history(event)
                        except Exception:
                            logger.exception("Falha ao registrar download no historico")
                    self._url_entry.setFocus()
                elif event.event_type == EventType.ERROR:
                    self._set_download_status("Erro no download.")
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
