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
    APP_VERSION,
    DEFAULT_DOWNLOADS_DIR,
    WINDOW_SIZE,
)
from youtube_downloader.ui.nav_sidebar import NavSidebar
from youtube_downloader.ui.theme import (
    ACCENT,
    APP_BG,
    BTN_SECONDARY,
    CARD_BORDER,
    CARD_STYLE,
    FONT_TITLE,
    GHOST_BTN,
    ICON_BTN,
    PRIMARY_BTN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    add_history_entry,
    load_history,
    remove_history_entry,
)
from youtube_downloader.core.download_queue import DownloadQueue
from youtube_downloader.core.downloader import YoutubeDownloader
from youtube_downloader.core.ffmpeg_utils import is_bundled_ffmpeg
from youtube_downloader.core.logging_config import (
    LOG_CACHE_DIR,
    LOG_DIR,
    get_logger,
)
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.notifications import notify_download_complete
from youtube_downloader.core.settings import AppSettings, load_settings, save_settings
from youtube_downloader.ui.downloads_view import DownloadsView
from youtube_downloader.ui.history_view import HistoryView
from youtube_downloader.ui.library_view import LibraryView
from youtube_downloader.ui.settings_view import SettingsView

logger = get_logger("app")

SECTION_PADX = 24


class YoutubeDownloaderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self._settings = load_settings()
        ctk.set_appearance_mode(self._settings.appearance_mode)
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(820, 600)
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

    def _build_top_bar(self) -> None:
        top = ctk.CTkFrame(self, fg_color=APP_BG, corner_radius=0, height=52)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(2, weight=1)
        top.grid_propagate(False)

        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SECTION_PADX, pady=10)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            inner,
            text=APP_TITLE,
            font=ctk.CTkFont(family=FONT_TITLE[0], size=FONT_TITLE[1], weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.grid(row=0, column=2, sticky="e")
        ctk.CTkButton(
            actions, text="⚙", command=self._open_settings, **ICON_BTN
        ).grid(row=0, column=0, padx=4)
        ctk.CTkButton(actions, text="?", command=self._show_about, **ICON_BTN).grid(
            row=0, column=1, padx=4
        )

        ctk.CTkFrame(self, height=1, fg_color=CARD_BORDER, corner_radius=0).grid(
            row=1, column=0, sticky="ew"
        )

    def _on_nav_select(self, view_id: str) -> None:
        self._switch_view(view_id)

    def _switch_view(self, view_id: str) -> None:
        for vid, frame in self._view_frames.items():
            if vid == view_id:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_remove()
        if view_id == "history" and self._history_view is not None:
            self._history_view.set_entries(self._history_entries)
        if view_id == "library" and self._library_view is not None:
            self._library_view.refresh()

    def _add_history_entry(
        self,
        filepath: str,
        title: Optional[str] = None,
        source_url: str = "",
    ) -> None:
        if not os.path.isfile(filepath):
            return
        label = (title or "").strip() or os.path.basename(filepath)
        entry = DownloadHistoryEntry.from_filepath(filepath, label, source_url)
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

    def _remove_history_entry(self, filepath: str) -> None:
        self._history_entries = remove_history_entry(filepath)
        if self._history_view is not None:
            self._history_view.set_entries(self._history_entries)

    def _enqueue_download_url(self, url: str) -> None:
        self._download_queue.add(url)

    def _get_queue_count(self) -> int:
        return len(self._download_queue)

    def _start_next_queued_if_idle(self) -> None:
        if self._downloads_view is None or self._downloads_view.is_downloading:
            return
        next_url = self._download_queue.pop_next()
        if not next_url:
            return
        self._downloads_view.refresh_queue_label()
        self._downloads_view.start_download_for_url(next_url)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_top_bar()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._sidebar = NavSidebar(body, on_select=self._on_nav_select)
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
            get_queue_count=self._get_queue_count,
            initial_output_dir=str(DEFAULT_DOWNLOADS_DIR),
        )
        self._view_frames["download"] = self._downloads_view

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
            download_playlist=collected.download_playlist,
        )
        save_settings(self._settings)

    def _on_close(self) -> None:
        self._persist_settings()
        self.destroy()

    def _show_about(self) -> None:
        if self._about_window is not None:
            try:
                if self._about_window.winfo_exists():
                    self._about_window.lift()
                    self._about_window.focus()
                    return
            except tk.TclError:
                self._about_window = None

        import yt_dlp

        from youtube_downloader.core.ffmpeg_utils import find_ffmpeg_dir

        ffmpeg_path = find_ffmpeg_dir() or "não encontrado"
        dialog = ctk.CTkToplevel(self)
        dialog.title("Sobre")
        dialog.geometry("440x280")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=APP_BG)
        self._about_window = dialog
        dialog.bind("<Destroy>", lambda _e: setattr(self, "_about_window", None))

        accent_bar = ctk.CTkFrame(dialog, height=3, fg_color=ACCENT, corner_radius=0)
        accent_bar.pack(fill="x")

        top = ctk.CTkFrame(dialog, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 8))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top,
            text="Sobre",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            top,
            text="✕",
            width=28,
            height=28,
            command=dialog.destroy,
            **GHOST_BTN,
        ).grid(row=0, column=1)

        body = ctk.CTkFrame(dialog, fg_color="transparent")
        body.pack(fill="x", padx=20)
        ctk.CTkLabel(
            body,
            text=f"{APP_TITLE} v{APP_VERSION}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            body,
            text=f"yt-dlp: {yt_dlp.version.__version__}",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(8, 2))
        ctk.CTkLabel(
            body,
            text=f"FFmpeg: {ffmpeg_path}",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkFrame(body, height=1, fg_color=CARD_STYLE["border_color"]).pack(
            fill="x", pady=(14, 10)
        )

        shortcuts = ctk.CTkFrame(dialog, fg_color="transparent")
        shortcuts.pack(fill="x", padx=20)
        ctk.CTkLabel(
            shortcuts,
            text="Atalhos:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        def _pill(parent: ctk.CTkFrame, key: str, desc: str, col: int) -> None:
            ctk.CTkLabel(
                parent,
                text=key,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=TEXT_PRIMARY,
                fg_color=BTN_SECONDARY,
                corner_radius=4,
                width=52,
                height=24,
            ).grid(row=1, column=col * 2, padx=(0, 6))
            ctk.CTkLabel(
                parent,
                text=desc,
                font=ctk.CTkFont(size=12),
                text_color=TEXT_SECONDARY,
                anchor="w",
            ).grid(row=1, column=col * 2 + 1, padx=(0, 16), sticky="w")

        _pill(shortcuts, "Ctrl+V", "colar URL", 0)
        _pill(shortcuts, "Ctrl+,", "preferências", 1)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(16, 20))
        ctk.CTkButton(
            btn_row,
            text="Ver logs",
            width=100,
            command=self._open_logs,
            **SECONDARY_BTN,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row,
            text="OK",
            width=100,
            command=dialog.destroy,
            **PRIMARY_BTN,
        ).pack(side="left")

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

    def _on_download_worker_finished(self) -> None:
        if self._downloads_view is not None and self._downloads_view.is_downloading:
            logger.warning(
                "Worker de download terminou, mas a UI ainda esta em modo download"
            )
            self._downloads_view.force_release_download_ui()
        self._start_next_queued_if_idle()

    def _poll_queue(self) -> None:
        while True:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle_event(event)
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
        self.after(50, self._poll_queue)

    def _handle_event(self, event: ProgressEvent) -> None:
        if self._downloads_view is not None:
            self._downloads_view.handle_progress_event(event)

        job = self._active_download_job
        if job is None:
            return

        if event.event_type == EventType.DONE:
            try:
                if job.notify_on_complete:
                    name = event.title or (
                        os.path.basename(event.filepath) if event.filepath else "Download"
                    )
                    notify_download_complete(
                        APP_TITLE,
                        f"Download concluído: {name}",
                    )
            except Exception:
                logger.exception("Falha ao exibir notificacao de download")
            self._active_download_job = None
            self._start_next_queued_if_idle()
        elif event.event_type in (EventType.ERROR, EventType.CANCELLED):
            self._active_download_job = None


def run() -> None:
    from youtube_downloader.core.logging_config import install_exception_hooks, setup_logging

    setup_logging()
    install_exception_hooks()
    logger.info("Aplicativo iniciado")
    app = YoutubeDownloaderApp()
    app.mainloop()
