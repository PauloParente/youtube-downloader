"""Main application window (PySide6)."""

from __future__ import annotations

import os
import threading
from dataclasses import replace
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QFrame, QMainWindow, QStackedWidget, QWidget

from youtube_downloader.config import (
    APP_TITLE,
    DEFAULT_DOWNLOADS_DIR,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_SIZE,
)
from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    add_history_entry,
    clear_history,
    entry_disk_signature,
    load_history,
    refresh_entries_from_disk,
    remove_history_entry,
    save_history,
    save_history_thumbnail,
)
from youtube_downloader.core.download_queue import DownloadQueue
from youtube_downloader.core.downloader import YoutubeDownloader
from youtube_downloader.core.ffmpeg_utils import is_bundled_ffmpeg
from youtube_downloader.core.logging_config import (
    LOG_CACHE_DIR,
    LOG_DIR,
    get_logger,
)
from youtube_downloader.core.metadata import VideoPreview, fetch_preview, is_youtube_url
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.notifications import notify_download_complete
from youtube_downloader.core.path_utils import open_path_in_explorer
from youtube_downloader.core.preview_cache import PreviewCache
from youtube_downloader.core.queue_coordinator import (
    is_terminal_download_event,
    should_start_next_job,
    should_sync_queue_structure,
)
from youtube_downloader.core.settings import AppSettings, load_settings, save_settings
from youtube_downloader.ui_qt.about_dialog import show_about_dialog
from youtube_downloader.ui_qt.download_worker import start_download_thread
from youtube_downloader.ui_qt.downloads_view import DownloadsView
from youtube_downloader.ui_qt.event_bridge import EventBridge
from youtube_downloader.ui_qt.history_view import HistoryView
from youtube_downloader.ui_qt.library_view import LibraryView
from youtube_downloader.ui_qt.nav_sidebar import NavSidebar
from youtube_downloader.ui_qt.queue_view import QueueView
from youtube_downloader.ui_qt.settings_view import SettingsView
from youtube_downloader.ui_qt.splash_screen import SplashScreen, center_on_screen, parse_window_size
from youtube_downloader.ui_qt.theme import apply_theme
from youtube_downloader.ui_qt.util import run_on_main, schedule

logger = get_logger("app")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._settings = load_settings()
        apply_theme(QApplication.instance(), self._settings.appearance_mode)

        self._downloader = YoutubeDownloader()
        self._event_bridge = EventBridge()
        self._event_bridge.progress.connect(self._handle_event)
        self._download_queue = DownloadQueue()
        self._preview_cache = PreviewCache()
        self._preview_cache.on_updated(self._on_preview_cache_updated)
        self._history_entries: list[DownloadHistoryEntry] = load_history()
        self._download_thread: Optional[threading.Thread] = None
        self._active_download_job: Optional[DownloadJob] = None
        self._qthread = None

        self._downloads_view: Optional[DownloadsView] = None
        self._queue_view: Optional[QueueView] = None
        self._history_view: Optional[HistoryView] = None
        self._library_view: Optional[LibraryView] = None
        self._settings_view: Optional[SettingsView] = None
        self._sidebar: Optional[NavSidebar] = None
        self._stack: Optional[QStackedWidget] = None
        self._ffmpeg_status_timer = False

        self._ensure_downloads_dir()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._build_ui()
        self._bind_shortcuts()
        self._apply_settings(self._settings)
        self._check_ffmpeg()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        from PySide6.QtWidgets import QHBoxLayout

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = NavSidebar(self._on_nav_select, self._show_about)
        layout.addWidget(self._sidebar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        layout.addWidget(sep)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        self._downloads_view = DownloadsView(
            event_bridge=self._event_bridge,
            preview_cache=self._preview_cache,
            on_start_download=self._run_download_job,
            on_cancel_download=self._downloader.cancel,
            on_persist_settings=self._persist_settings,
            on_record_history=self._record_history_from_download_event,
            on_get_app_settings=lambda: self._settings,
            on_enqueue_url=self._enqueue_download_url,
            on_enqueue_urls=self._enqueue_download_urls,
            get_queue_snapshot=self._get_queue_snapshot,
            on_remove_queue_at=self._remove_queue_at,
            on_clear_queue=self._clear_download_queue,
            pop_next_queue_url=self._pop_next_queue_url,
            on_sync_queue_structure=self._sync_queue_structure,
            on_sync_now_playing=self._sync_now_playing_panel,
        )
        self._stack.addWidget(self._downloads_view)

        self._queue_view = QueueView(
            get_queue_snapshot=self._get_queue_snapshot,
            get_cached_preview=self._preview_cache.get,
            get_card_thumb=self._preview_cache.get_card_thumb,
            is_preview_pending=self._preview_cache.is_pending,
            on_remove_queue_at=self._remove_queue_at,
            on_cancel_download=lambda: (
                self._downloads_view.cancel_download() if self._downloads_view else None
            ),
            on_skip_download=lambda: (
                self._downloads_view.skip_to_next_download()
                if self._downloads_view
                else None
            ),
        )
        self._stack.addWidget(self._queue_view)

        self._library_view = LibraryView(
            get_output_dir=lambda: self._settings.output_dir,
            on_open_path=self._open_path_in_explorer,
        )
        self._stack.addWidget(self._library_view)

        self._history_view = HistoryView(
            on_open_folder=self._open_history_folder,
            on_open_file=self._open_history_file,
            on_redownload=self._redownload_from_history,
            on_remove=self._remove_history_entry,
            on_clear_history=self._clear_history,
        )
        self._history_view.set_entries(self._history_entries)
        self._stack.addWidget(self._history_view)

        self._settings_view = SettingsView(on_save=self._on_settings_saved)
        self._settings_view.load_settings(self._settings)
        self._stack.addWidget(self._settings_view)

        self._switch_view("download")

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+V"), self, self._on_ctrl_v)
        QShortcut(QKeySequence("Ctrl+,"), self, self._open_settings)

    def _on_nav_select(self, view_id: str) -> None:
        self._switch_view(view_id)

    def _switch_view(self, view_id: str) -> None:
        if self._stack is None or self._sidebar is None:
            return
        index = {
            "download": 0,
            "queue": 1,
            "library": 2,
            "history": 3,
            "settings": 4,
        }.get(view_id, 0)
        self._stack.setCurrentIndex(index)
        self._sidebar.set_active(view_id)
        if view_id == "history":
            self._refresh_history_from_disk()
            if self._history_view:
                self._history_view.set_entries(self._history_entries)
        if view_id == "library" and self._library_view:
            self._library_view.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_settings()
        super().closeEvent(event)

    def _on_preview_cache_updated(self, url: str) -> None:
        run_on_main(self, lambda u=url: self._handle_preview_cache_updated(u))

    def _handle_preview_cache_updated(self, url: str) -> None:
        if self._queue_view:
            self._queue_view.update_card(url)
        if self._downloads_view and self._downloads_view.is_downloading:
            cleaned = url.strip()
            if self._downloads_view.current_url.strip() == cleaned:
                preview = self._preview_cache.get(cleaned)
                if preview and preview.title:
                    self._downloads_view.set_now_playing_title(preview.title)
                self._sync_now_playing_panel()

    def _sync_now_playing_panel(self) -> None:
        if self._queue_view is None or self._downloads_view is None:
            return
        meta = self._downloads_view.get_now_playing_meta()
        self._queue_view.set_thumbnail_bytes(meta.get("thumbnail_bytes"))
        self._queue_view.set_now_playing(
            active=meta["active"],
            url=meta["url"],
            title=meta["title"],
            status=meta["status"],
            percent=meta["percent"],
        )

    def _sync_queue_structure(self) -> None:
        if self._queue_view:
            self._queue_view.refresh()
            self._sync_now_playing_panel()

    def _prefetch_queue_urls(self, urls: list[str]) -> None:
        if urls:
            self._preview_cache.request(urls)

    def _enqueue_download_url(self, url: str) -> bool:
        added = self._download_queue.add(url)
        if added:
            self._prefetch_queue_urls([url])
            self._sync_queue_structure()
        return added

    def _enqueue_download_urls(self, urls: list[str]) -> int:
        before = set(self._download_queue.snapshot())
        added = self._download_queue.add_many(urls)
        if added:
            new_urls = [u for u in self._download_queue.snapshot() if u not in before]
            self._prefetch_queue_urls(new_urls)
            self._sync_queue_structure()
        return added

    def _get_queue_snapshot(self) -> list[str]:
        return self._download_queue.snapshot()

    def _remove_queue_at(self, index: int) -> None:
        if self._download_queue.remove_at(index):
            self._sync_queue_structure()
            if self._downloads_view:
                self._downloads_view.append_log(f"Removido da fila (posição {index + 1}).")

    def _clear_download_queue(self) -> None:
        if not self._download_queue.snapshot():
            return
        self._download_queue.clear()
        self._sync_queue_structure()
        if self._downloads_view:
            self._downloads_view.append_log("Fila esvaziada.")

    def _pop_next_queue_url(self) -> str | None:
        url = self._download_queue.pop_next()
        if url:
            self._sync_queue_structure()
        return url

    def _download_worker_alive(self) -> bool:
        return self._qthread is not None and self._qthread.isRunning()

    def _start_next_queued_if_idle(self) -> None:
        if self._downloads_view is None:
            return
        if self._active_download_job is not None or self._download_worker_alive():
            return
        next_url = self._download_queue.pop_next()
        if not next_url:
            return
        if self._queue_view:
            self._queue_view.reconcile_pending()
        self._downloads_view.continue_queue_for_url(next_url)

    def _add_history_entry(
        self,
        filepath: str,
        title: Optional[str] = None,
        source_url: str = "",
        *,
        channel_name: str = "",
        channel_url: str = "",
        thumbnail_bytes: Optional[bytes] = None,
        thumbnail_path: str = "",
    ) -> None:
        if not os.path.isfile(filepath):
            return
        label = (title or "").strip() or os.path.basename(filepath)
        thumb_path = thumbnail_path
        if not thumb_path and thumbnail_bytes and source_url.strip():
            thumb_path = save_history_thumbnail(source_url, thumbnail_bytes)
        entry = DownloadHistoryEntry.from_filepath(
            filepath,
            label,
            source_url,
            channel_name=channel_name,
            channel_url=channel_url,
            thumbnail_path=thumb_path,
        )
        self._history_entries = add_history_entry(entry)
        if self._history_view and self._sidebar and self._sidebar._active_id == "history":
            self._history_view.set_entries(self._history_entries)

    def _add_history_entry_async(self, **kwargs) -> None:
        def worker() -> None:
            filepath = kwargs.get("filepath", "")
            if not os.path.isfile(filepath):
                return
            thumb_path = ""
            tb = kwargs.get("thumbnail_bytes")
            su = kwargs.get("source_url", "")
            if tb and su.strip():
                thumb_path = save_history_thumbnail(su, tb)
            label = (kwargs.get("title") or "").strip() or os.path.basename(filepath)
            entry = DownloadHistoryEntry.from_filepath(
                filepath,
                label,
                su,
                channel_name=kwargs.get("channel_name", ""),
                channel_url=kwargs.get("channel_url", ""),
                thumbnail_path=thumb_path,
            )
            try:
                entries = add_history_entry(entry)
            except Exception:
                logger.exception("Falha ao gravar historico em background")
                return

            def on_main() -> None:
                self._history_entries = entries
                if (
                    self._history_view
                    and self._sidebar
                    and self._sidebar._active_id == "history"
                ):
                    self._history_view.set_entries(entries)

            run_on_main(self, on_main)

        threading.Thread(target=worker, daemon=True).start()

    def _record_history_from_download_event(self, event: ProgressEvent) -> None:
        filepath = event.filepath
        if not filepath or not os.path.isfile(filepath) or not self._downloads_view:
            return
        source_url = self._downloads_view.current_url
        meta = self._preview_cache.get(source_url)
        defer_disk = bool(self._download_queue.snapshot())

        def build_fields(preview: Optional[VideoPreview]) -> dict:
            title = (event.title or "").strip()
            if not title and preview and preview.title:
                title = preview.title.strip()
            if not title:
                title = os.path.basename(filepath)
            return {
                "filepath": filepath,
                "title": title,
                "source_url": source_url,
                "channel_name": (preview.uploader or "").strip() if preview else "",
                "channel_url": (preview.channel_url or "").strip() if preview else "",
                "thumbnail_bytes": (
                    preview.thumbnail_bytes if preview and preview.thumbnail_bytes else None
                ),
            }

        def resolve_preview() -> Optional[VideoPreview]:
            if meta is not None and not meta.error:
                return meta
            if not source_url or not is_youtube_url(source_url):
                return None
            try:
                fetched = fetch_preview(source_url)
            except Exception:
                logger.exception("Metadados do historico (fallback): %s", source_url[:80])
                return None
            if fetched and not fetched.error:
                self._preview_cache.put(fetched)
                return fetched
            return None

        if defer_disk:
            def worker() -> None:
                fields = build_fields(resolve_preview())
                self._add_history_entry_async(**fields)

            threading.Thread(target=worker, daemon=True).start()
            return

        fields = build_fields(meta if meta and not meta.error else None)
        if fields["thumbnail_bytes"] is None and source_url and is_youtube_url(source_url):

            def worker() -> None:
                resolved = build_fields(resolve_preview())
                run_on_main(self, lambda f=resolved: self._add_history_entry(**f))

            threading.Thread(target=worker, daemon=True).start()
            return

        self._add_history_entry(**fields)

    def _open_history_folder(self, filepath: str) -> None:
        if os.path.isfile(filepath):
            folder = os.path.dirname(filepath)
            if os.path.isdir(folder):
                self._open_path_in_explorer(folder)
        elif os.path.isdir(filepath):
            self._open_path_in_explorer(filepath)

    def _open_history_file(self, filepath: str) -> None:
        if os.path.isfile(filepath):
            self._open_path_in_explorer(filepath)

    def _redownload_from_history(self, url: str, _title: str) -> None:
        cleaned = url.strip()
        if not cleaned:
            return
        self._switch_view("download")
        if self._sidebar:
            self._sidebar.set_active("download")
        if self._downloads_view:
            self._downloads_view.set_url_and_focus(cleaned)
            self._downloads_view.show_status_hint(
                "URL do histórico colada. Clique em Baixar para iniciar."
            )

    def _refresh_history_from_disk(self) -> None:
        refreshed = refresh_entries_from_disk(self._history_entries)
        old_sig = [entry_disk_signature(e) for e in self._history_entries]
        new_sig = [entry_disk_signature(e) for e in refreshed]
        if old_sig != new_sig:
            self._history_entries = refreshed
            save_history(refreshed)

    def _clear_history(self) -> list[DownloadHistoryEntry]:
        self._history_entries = clear_history()
        return self._history_entries

    def _remove_history_entry(self, filepath: str) -> list[DownloadHistoryEntry]:
        self._history_entries = remove_history_entry(filepath)
        return self._history_entries

    def _on_ctrl_v(self) -> None:
        if self._downloads_view and not self._downloads_view.is_downloading:
            self._downloads_view.paste_url()

    def _open_settings(self) -> None:
        if self._downloads_view and self._downloads_view.is_downloading:
            return
        self._switch_view("settings")
        if self._settings_view:
            self._settings_view.load_settings(self._settings)

    def _on_settings_saved(self, settings: AppSettings) -> None:
        if self._downloads_view and self._downloads_view.is_downloading:
            return
        self._settings = settings
        save_settings(settings)
        self._apply_settings(settings)

    def _show_temporary_status(self, message: str, delay_ms: int = 8000) -> None:
        if self._downloads_view:
            self._downloads_view.set_download_status(message)
        schedule(self, delay_ms, self._clear_temporary_status)

    def _clear_temporary_status(self) -> None:
        if self._downloads_view and not self._downloads_view.is_downloading:
            self._downloads_view.reset_download_status()

    def _ensure_downloads_dir(self) -> None:
        DEFAULT_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    def _check_ffmpeg(self) -> None:
        if is_bundled_ffmpeg():
            return
        if YoutubeDownloader.ffmpeg_available():
            self._show_temporary_status(
                "Aviso: FFmpeg do sistema. Para distribuir, use .\\build.ps1."
            )
            return
        self._show_temporary_status(
            "Erro: FFmpeg não encontrado. Use build.ps1 ou instale no PATH."
        )

    def _apply_settings(self, settings: AppSettings) -> None:
        apply_theme(QApplication.instance(), settings.appearance_mode)
        if self._downloads_view:
            self._downloads_view.apply_settings(settings)
        if self._settings_view:
            self._settings_view.load_settings(settings)

    def _persist_settings(self) -> None:
        if self._downloads_view is None:
            return
        collected = self._downloads_view.collect_settings()
        self._settings = replace(
            self._settings,
            output_dir=collected.output_dir,
            quality=collected.quality,
            audio_only=collected.audio_only,
        )
        save_settings(self._settings)

    def _show_about(self) -> None:
        try:
            show_about_dialog(self, on_open_logs=self._open_logs)
        except Exception:
            logger.exception("Falha ao abrir diálogo Sobre")

    def _open_path_in_explorer(self, path: str) -> None:
        try:
            open_path_in_explorer(path)
        except OSError as exc:
            logger.exception("Falha ao abrir caminho: %s", path)
            if self._downloads_view:
                self._downloads_view.set_download_status(f"Erro ao abrir: {exc}")

    def _open_logs(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._open_path_in_explorer(str(LOG_DIR))

    def _run_download_job(self, job: DownloadJob) -> None:
        if self._downloads_view is None:
            return
        self._active_download_job = job
        self._qthread = start_download_thread(
            self._downloader,
            job,
            on_progress=self._event_bridge.emit_progress,
            on_finished=self._on_download_worker_finished,
        )

    def _on_download_worker_finished(self) -> None:
        self._qthread = None
        if self._downloads_view is None or not self._downloads_view.is_downloading:
            return
        if self._download_worker_alive() or self._active_download_job is not None:
            return
        if self._download_queue.snapshot():
            self._start_next_queued_if_idle()
            return
        logger.warning(
            "Worker terminou com UI em modo download sem fila; recuperando controles"
        )
        self._downloads_view.force_release_download_ui()

    def _handle_event(self, event: ProgressEvent) -> None:
        try:
            if self._downloads_view:
                self._downloads_view.handle_progress_event(event)
            if self._queue_view and self._downloads_view:
                self._queue_view.apply_progress_event(event)
                if event.event_type in (
                    EventType.PROGRESS,
                    EventType.LOG,
                    EventType.DONE,
                    EventType.ERROR,
                    EventType.CANCELLED,
                ):
                    self._sync_now_playing_panel()
                if is_terminal_download_event(event.event_type):
                    continue_after_cancel = False
                    is_downloading = self._downloads_view.is_downloading
                    if is_downloading and event.event_type == EventType.CANCELLED:
                        continue_after_cancel = (
                            self._downloads_view.should_continue_queue_after_cancel()
                        )
                    if should_sync_queue_structure(
                        event.event_type,
                        is_downloading=is_downloading,
                        queue_has_items=bool(self._get_queue_snapshot()),
                        continue_after_cancel=continue_after_cancel,
                    ):
                        self._sync_queue_structure()

            job = self._active_download_job
            if job is None:
                return

            if event.event_type == EventType.DONE:
                try:
                    if job.notify_on_complete:
                        name = event.title or (
                            os.path.basename(event.filepath)
                            if event.filepath
                            else "Download"
                        )
                        notify_download_complete(APP_TITLE, f"Download concluído: {name}")
                except Exception:
                    logger.exception("Falha ao exibir notificacao de download")
                self._active_download_job = None
                self._start_next_queued_if_idle()
            elif event.event_type == EventType.CANCELLED:
                self._active_download_job = None
                continue_after_cancel = (
                    self._downloads_view is not None
                    and self._downloads_view.should_continue_queue_after_cancel()
                )
                if should_start_next_job(
                    event.event_type, continue_after_cancel=continue_after_cancel
                ):
                    self._start_next_queued_if_idle()
            elif event.event_type == EventType.ERROR:
                self._active_download_job = None
        except Exception:
            logger.exception("Erro ao processar evento: %s", event.event_type.value)
            if self._downloads_view and event.event_type in (
                EventType.DONE,
                EventType.ERROR,
                EventType.CANCELLED,
            ):
                self._downloads_view.force_release_download_ui()
            self._active_download_job = None


def run() -> None:
    from youtube_downloader.core.logging_config import install_exception_hooks, setup_logging

    setup_logging()
    install_exception_hooks()
    logger.info("Aplicativo iniciado (PySide6)")

    app = QApplication.instance() or QApplication([])
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    window = MainWindow()
    w, h = parse_window_size(WINDOW_SIZE)
    window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
    window.resize(w, h)
    window.setWindowTitle(APP_TITLE)
    center_on_screen(window)
    splash.finish(window)
    window.show()
    app.exec()
