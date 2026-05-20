"""Main application window."""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import replace
from typing import Optional

import customtkinter as ctk

from youtube_downloader.config import (
    APP_TITLE,
    DEFAULT_DOWNLOADS_DIR,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_SIZE,
)
from youtube_downloader.ui.nav_sidebar import NavSidebar
from youtube_downloader.ui.theme import (
    APP_BG,
    CARD_BORDER,
    CARD_STYLE,
    PRIMARY_BTN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
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
    install_ui_exception_logging,
)
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.notifications import notify_download_complete
from youtube_downloader.core.settings import AppSettings, load_settings, save_settings
from youtube_downloader.ui.about_dialog import show_about_dialog
from youtube_downloader.ui.downloads_view import DownloadsView
from youtube_downloader.ui.queue_view import QueueView
from youtube_downloader.ui.history_view import HistoryView
from youtube_downloader.ui.library_view import LibraryView
from youtube_downloader.ui.settings_view import SettingsView

logger = get_logger("app")


class YoutubeDownloaderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        install_ui_exception_logging(self)

        self._settings = load_settings()
        ctk.set_appearance_mode(self._settings.appearance_mode)
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=APP_BG)

        self._view_frames: dict[str, ctk.CTkFrame] = {}
        self._sidebar: Optional[NavSidebar] = None
        self._history_entries: list[DownloadHistoryEntry] = load_history()
        self._history_view: Optional[HistoryView] = None
        self._library_view: Optional[LibraryView] = None

        self._downloader = YoutubeDownloader()
        self._event_queue: queue.Queue[ProgressEvent] = queue.Queue()
        self._download_queue = DownloadQueue()
        self._downloads_view: Optional[DownloadsView] = None
        self._queue_view: Optional[QueueView] = None
        self._download_thread: Optional[threading.Thread] = None
        self._active_download_job: Optional[DownloadJob] = None
        self._settings_view: Optional[SettingsView] = None
        self._about_window: Optional[ctk.CTkToplevel] = None
        self._ffmpeg_status_after_id: Optional[str] = None

        self._ensure_downloads_dir()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._build_ui()
        self._bind_shortcuts()
        self._apply_settings(self._settings)
        self._check_ffmpeg()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._poll_queue)

    def _on_nav_select(self, view_id: str) -> None:
        self._switch_view(view_id)

    def _switch_view(self, view_id: str) -> None:
        for vid, frame in self._view_frames.items():
            if vid == view_id:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_remove()
        if view_id == "history":
            self._refresh_history_from_disk()
            if self._history_view is not None:
                self._history_view.set_entries(self._history_entries)
        if view_id == "library" and self._library_view is not None:
            self._library_view.refresh()

    def _add_history_entry(
        self,
        filepath: str,
        title: Optional[str] = None,
        source_url: str = "",
        *,
        channel_name: str = "",
        channel_url: str = "",
        thumbnail_bytes: Optional[bytes] = None,
    ) -> None:
        if not os.path.isfile(filepath):
            return
        label = (title or "").strip() or os.path.basename(filepath)
        thumb_path = ""
        if thumbnail_bytes and source_url.strip():
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
        if self._history_view is not None:
            self._history_view.set_entries(self._history_entries)

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
        if self._downloads_view is not None:
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

    def _sync_queue_ui(self) -> None:
        if self._queue_view is None:
            return
        self._queue_view.refresh()
        if self._downloads_view is not None:
            meta = self._downloads_view.get_now_playing_meta()
            self._queue_view.set_thumbnail_bytes(meta.get("thumbnail_bytes"))
            self._queue_view.set_now_playing(
                active=meta["active"],
                url=meta["url"],
                title=meta["title"],
                status=meta["status"],
                percent=meta["percent"],
            )

    def _enqueue_download_url(self, url: str) -> bool:
        added = self._download_queue.add(url)
        if added:
            self._sync_queue_ui()
        return added

    def _enqueue_download_urls(self, urls: list[str]) -> int:
        added = self._download_queue.add_many(urls)
        if added:
            self._sync_queue_ui()
        return added

    def _get_queue_snapshot(self) -> list[str]:
        return self._download_queue.snapshot()

    def _remove_queue_at(self, index: int) -> None:
        if self._download_queue.remove_at(index):
            self._sync_queue_ui()
            if self._downloads_view is not None:
                self._downloads_view.append_log(
                    f"Removido da fila (posição {index + 1})."
                )

    def _clear_download_queue(self) -> None:
        if not self._download_queue.snapshot():
            return
        self._download_queue.clear()
        self._sync_queue_ui()
        if self._downloads_view is not None:
            self._downloads_view.append_log("Fila esvaziada.")

    def _pop_next_queue_url(self) -> str | None:
        url = self._download_queue.pop_next()
        if url:
            self._sync_queue_ui()
        return url

    def _download_worker_alive(self) -> bool:
        return self._download_thread is not None and self._download_thread.is_alive()

    def _start_next_queued_if_idle(self) -> None:
        if self._downloads_view is None:
            return
        if self._active_download_job is not None or self._download_worker_alive():
            return
        next_url = self._download_queue.pop_next()
        if not next_url:
            return
        self._sync_queue_ui()
        self._downloads_view.start_download_for_url(next_url)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._sidebar = NavSidebar(
            body,
            on_select=self._on_nav_select,
            on_about=self._show_about,
        )
        self._sidebar.grid(row=0, column=0, sticky="ns")

        ctk.CTkFrame(body, width=1, fg_color=CARD_BORDER, corner_radius=0).grid(
            row=0, column=1, sticky="ns"
        )

        content = ctk.CTkFrame(body, fg_color="transparent")
        content.grid(row=0, column=2, sticky="nsew", padx=(0, 0))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._downloads_view = DownloadsView(
            content,
            event_queue=self._event_queue,
            on_start_download=self._run_download_job,
            on_cancel_download=self._downloader.cancel,
            on_persist_settings=self._persist_settings,
            on_add_history=self._add_history_entry,
            on_get_app_settings=lambda: self._settings,
            on_enqueue_url=self._enqueue_download_url,
            on_enqueue_urls=self._enqueue_download_urls,
            get_queue_snapshot=self._get_queue_snapshot,
            on_remove_queue_at=self._remove_queue_at,
            on_clear_queue=self._clear_download_queue,
            pop_next_queue_url=self._pop_next_queue_url,
            on_sync_queue_ui=self._sync_queue_ui,
            initial_output_dir=str(DEFAULT_DOWNLOADS_DIR),
        )
        self._view_frames["download"] = self._downloads_view

        self._queue_view = QueueView(
            content,
            get_queue_snapshot=self._get_queue_snapshot,
            on_remove_queue_at=self._remove_queue_at,
            on_cancel_download=lambda: (
                self._downloads_view.cancel_download()
                if self._downloads_view
                else None
            ),
            on_skip_download=lambda: (
                self._downloads_view.skip_to_next_download()
                if self._downloads_view
                else None
            ),
        )
        self._view_frames["queue"] = self._queue_view

        self._library_view = LibraryView(
            content,
            get_output_dir=lambda: self._settings.output_dir,
            on_open_path=self._open_path_in_explorer,
        )
        self._view_frames["library"] = self._library_view

        self._settings_view = SettingsView(content, on_save=self._on_settings_saved)
        self._view_frames["settings"] = self._settings_view
        self._settings_view.load_settings(self._settings)

        self._history_view = HistoryView(
            content,
            on_open_folder=self._open_history_folder,
            on_open_file=self._open_history_file,
            on_redownload=self._redownload_from_history,
            on_remove=self._remove_history_entry,
            on_clear_history=self._clear_history,
        )
        self._view_frames["history"] = self._history_view
        self._history_view.set_entries(self._history_entries)

        self._switch_view("download")

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-v>", self._on_ctrl_v)
        self.bind_all("<Control-comma>", self._on_ctrl_settings)

    def _on_ctrl_v(self, _event: Optional[object] = None) -> None:
        if self._downloads_view is not None and not self._downloads_view.is_downloading:
            self._downloads_view.paste_url()

    def _on_ctrl_settings(self, _event: Optional[object] = None) -> None:
        self._open_settings()

    def _open_settings(self) -> None:
        if self._downloads_view is not None and self._downloads_view.is_downloading:
            return
        self._switch_view("settings")
        if self._sidebar:
            self._sidebar.set_active("settings")
        if self._settings_view is not None:
            self._settings_view.load_settings(self._settings)

    def _on_settings_saved(self, settings: AppSettings) -> None:
        if self._downloads_view is not None and self._downloads_view.is_downloading:
            return
        self._settings = settings
        save_settings(settings)
        self._apply_settings(settings)

    def _show_temporary_status(self, message: str, delay_ms: int = 8000) -> None:
        if self._ffmpeg_status_after_id is not None:
            self.after_cancel(self._ffmpeg_status_after_id)
        if self._downloads_view is not None:
            self._downloads_view.set_download_status(message)
        self._ffmpeg_status_after_id = self.after(
            delay_ms, self._clear_temporary_status
        )

    def _clear_temporary_status(self) -> None:
        self._ffmpeg_status_after_id = None
        if self._downloads_view is not None and not self._downloads_view.is_downloading:
            self._downloads_view.reset_download_status()

    def _ensure_downloads_dir(self) -> None:
        DEFAULT_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    def _check_ffmpeg(self) -> None:
        if is_bundled_ffmpeg():
            logger.info("FFmpeg embutido detectado")
            return
        if YoutubeDownloader.ffmpeg_available():
            logger.warning("FFmpeg do sistema (nao embutido); use build.ps1 para distribuir")
            self._show_temporary_status(
                "Aviso: FFmpeg do sistema. Para distribuir, use .\\build.ps1."
            )
            return
        logger.error("FFmpeg nao encontrado; downloads de video/MP3 podem falhar")
        self._show_temporary_status(
            "Erro: FFmpeg não encontrado. Use build.ps1 ou instale no PATH."
        )

    def _apply_settings(self, settings: AppSettings) -> None:
        mode = settings.appearance_mode
        if mode in ("dark", "light"):
            ctk.set_appearance_mode(mode)
        if self._downloads_view is not None:
            self._downloads_view.apply_settings(settings)
        if self._settings_view is not None:
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

    def _on_close(self) -> None:
        self._persist_settings()
        self.destroy()

    def _show_about(self) -> None:
        try:
            dialog = show_about_dialog(
                self,
                on_open_logs=self._open_logs,
                existing=self._about_window,
            )
        except Exception:
            logger.exception("Falha ao abrir diálogo Sobre")
            return
        self._about_window = dialog
        dialog.bind("<Destroy>", lambda _e: setattr(self, "_about_window", None))

    def _open_path_in_explorer(self, path: str) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except OSError as exc:
            logger.exception("Falha ao abrir caminho: %s", path)
            if self._downloads_view is not None:
                self._downloads_view.set_download_status(f"Erro ao abrir: {exc}")

    def _open_logs(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._open_path_in_explorer(str(LOG_DIR))

    def _run_download_job(self, job: DownloadJob) -> None:
        if self._downloads_view is None:
            return
        self._active_download_job = job

        def worker() -> None:
            def on_event(event: ProgressEvent) -> None:
                self._event_queue.put(event)

            try:
                self._downloader.download(job, on_event)
            finally:
                self.after(0, self._on_download_worker_finished)

        self._download_thread = threading.Thread(target=worker, daemon=True)
        self._download_thread.start()

    def _drain_event_queue_sync(self) -> None:
        """Processa eventos pendentes na main thread (evita corrida com o fim do worker)."""
        while True:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)

    def _on_download_worker_finished(self) -> None:
        self._drain_event_queue_sync()
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

    def _poll_queue(self) -> None:
        while True:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
        self.after(50, self._poll_queue)

    def _handle_event(self, event: ProgressEvent) -> None:
        try:
            if self._downloads_view is not None:
                self._downloads_view.handle_progress_event(event)
            if self._queue_view is not None and self._downloads_view is not None:
                self._queue_view.apply_progress_event(event)
                if event.event_type in (
                    EventType.PROGRESS,
                    EventType.LOG,
                    EventType.DONE,
                    EventType.ERROR,
                    EventType.CANCELLED,
                ):
                    meta = self._downloads_view.get_now_playing_meta()
                    self._queue_view.set_thumbnail_bytes(meta.get("thumbnail_bytes"))
                    self._queue_view.set_now_playing(
                        active=meta["active"],
                        url=meta["url"],
                        title=meta["title"],
                        status=meta["status"],
                        percent=meta["percent"],
                    )
                if event.event_type in (
                    EventType.DONE,
                    EventType.CANCELLED,
                    EventType.ERROR,
                ):
                    self._sync_queue_ui()

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
                        notify_download_complete(
                            APP_TITLE,
                            f"Download concluído: {name}",
                        )
                except Exception:
                    logger.exception("Falha ao exibir notificacao de download")
                self._active_download_job = None
                self._start_next_queued_if_idle()
            elif event.event_type == EventType.CANCELLED:
                self._active_download_job = None
                if (
                    self._downloads_view is not None
                    and self._downloads_view.should_continue_queue_after_cancel()
                ):
                    self._start_next_queued_if_idle()
            elif event.event_type == EventType.ERROR:
                self._active_download_job = None
        except Exception:
            logger.exception(
                "Erro ao processar evento da fila: %s", event.event_type.value
            )
            if self._downloads_view is not None and event.event_type in (
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
    logger.info("Aplicativo iniciado")
    app = YoutubeDownloaderApp()
    app.mainloop()
