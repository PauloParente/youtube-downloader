"""Downloads screen — URL, preview, options, progress, and activity log."""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from typing import Literal, Optional

import customtkinter as ctk

from youtube_downloader.config import (
    DEFAULT_DOWNLOADS_DIR,
    DOWNLOADS_FOOTER_STACK_WIDTH,
    QUALITY_COMBO_VALUES,
    QUALITY_DISPLAY_LABELS,
    QUALITY_FROM_DISPLAY,
    QUALITY_OPTIONS,
)
from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import VideoPreview, is_youtube_url
from youtube_downloader.core.path_utils import open_path_in_explorer
from youtube_downloader.core.preview_cache import PreviewCache
from youtube_downloader.core.download_job_builder import build_download_job
from youtube_downloader.core.download_url_flow import (
    ResolvedUrlPlanKind,
    format_enqueue_log,
    format_playlist_download_start_log,
    needs_network_expand,
    plan_resolved_urls,
)
from youtube_downloader.core.playlist_urls import (
    PlaylistExpandError,
    PlaylistMode,
    UrlKind,
    classify_youtube_url,
    resolve_download_urls,
)
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.settings import AppSettings
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui.downloads_preview import DownloadsPreviewPanel
from youtube_downloader.ui.layout_utils import apply_wraplength_from_widget
from youtube_downloader.ui.playlist_choice_dialog import ask_video_in_playlist_choice
from youtube_downloader.ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    APP_BG,
    BTN_DISABLED,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    CARD_BORDER,
    CARD_STYLE,
    ENTRY_STYLE,
    FONT_BODY,
    PRIMARY_BTN,
    SECONDARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

logger = get_logger(__name__)

SECTION_GAP = 10
LOG_TEXTBOX_HEIGHT = 160
QUEUE_URL_TRUNCATE = 58
DEFAULT_STATUS_TEXT = "Pronto para baixar."


class DownloadsView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        event_queue: queue.Queue[ProgressEvent],
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
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._event_queue = event_queue
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
        self._status_reset_after_id: Optional[str] = None
        self._last_download_filepath: Optional[str] = None
        self._log_body: Optional[ctk.CTkFrame] = None
        self._log_expanded = True
        self._scroll_host: Optional[ctk.CTkFrame] = None
        self._scroll: Optional[ctk.CTkScrollableFrame] = None
        self._footer: Optional[ctk.CTkFrame] = None
        self._btn_row: Optional[ctk.CTkFrame] = None
        self._footer_layout_narrow = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_ui()

    @property
    def is_downloading(self) -> bool:
        return self._is_downloading

    @property
    def current_url(self) -> str:
        return self._url_entry.get().strip()

    def set_now_playing_title(self, title: str) -> None:
        self._now_playing_title = title.strip() or None

    def collect_settings(self) -> AppSettings:
        return self._collect_settings()

    def apply_settings(self, settings: AppSettings) -> None:
        if settings.quality in QUALITY_OPTIONS:
            self._set_quality_combo(settings.quality)
        self._audio_only_var.set(settings.audio_only)
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
        url = self._url_entry.get().strip()
        cached = self._preview_cache.get(url)
        title = (self._now_playing_title or "").strip()
        if not title and cached and cached.title:
            title = cached.title.strip()
        preview = self._preview_panel.current_preview if self._preview_panel else None
        if not title and preview and preview.title:
            title = preview.title.strip()
        status = DEFAULT_STATUS_TEXT
        if hasattr(self, "_status_label"):
            status = self._status_label.cget("text") or status
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
        self._url_entry.delete(0, "end")
        self._url_entry.insert(0, url)
        self._url_entry.focus_set()
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
        self._url_entry.delete(0, "end")
        self._url_entry.insert(0, cleaned)
        self._schedule_preview_if_ready()
        self._run_download_job_for_url(cleaned)

    def continue_queue_for_url(self, url: str) -> None:
        """Start next queued item without heavy UI reset (batch advance)."""
        cleaned = url.strip()
        if not cleaned:
            return
        self._url_entry.delete(0, "end")
        self._url_entry.insert(0, cleaned)
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
        display = self._quality_combo.get()
        return QUALITY_FROM_DISPLAY.get(display, QUALITY_OPTIONS[0])

    def _set_quality_combo(self, quality: str) -> None:
        label = QUALITY_DISPLAY_LABELS.get(quality, QUALITY_DISPLAY_LABELS[QUALITY_OPTIONS[0]])
        self._quality_combo.set(label)

    def _update_progress_percent(self, percent: Optional[float]) -> None:
        self._last_progress_percent = percent

    def _toggle_log_panel(self) -> None:
        if self._log_body is None:
            return
        self._log_expanded = not self._log_expanded
        if self._log_expanded:
            self._log_body.grid(row=0, column=0, sticky="nsew")
            self._log_toggle_btn.configure(text="▼")
        else:
            self._log_body.grid_remove()
            self._log_toggle_btn.configure(text="▶")

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        cp = 20

        # Host does not grow with scroll content — keeps viewport above the fixed footer.
        self._scroll_host = ctk.CTkFrame(self, fg_color="transparent")
        self._scroll_host.grid(row=0, column=0, sticky="nsew")
        self._scroll_host.grid_propagate(False)
        self._scroll_host.grid_rowconfigure(0, weight=1)
        self._scroll_host.grid_columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(self._scroll_host, fg_color="transparent")
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        self.bind("<Configure>", self._on_view_configure)

        scroll = self._scroll

        ctk.CTkLabel(
            scroll,
            text="URL do YouTube",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=cp, pady=(4, 6), sticky="ew")

        url_outer = ctk.CTkFrame(scroll, fg_color="transparent")
        url_outer.grid(row=1, column=0, padx=cp, pady=(0, SECTION_GAP), sticky="ew")
        url_outer.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            url_outer, text="🔗", width=28, font=ctk.CTkFont(size=16), text_color=TEXT_MUTED
        ).grid(row=0, column=0, padx=(4, 0))
        self._url_entry = ctk.CTkEntry(
            url_outer,
            placeholder_text="Cole o link do vídeo ou playlist aqui...",
            **ENTRY_STYLE,
        )
        self._url_entry.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        self._url_entry.bind("<<Paste>>", lambda _e: self._schedule_preview_if_ready())
        self._url_entry.bind("<KeyRelease>", lambda _e: self._schedule_preview_if_ready())
        self._preview_panel = DownloadsPreviewPanel(
            self,
            url_entry=self._url_entry,
            event_queue=self._event_queue,
            preview_cache=self._preview_cache,
            is_downloading=lambda: self._is_downloading,
        )
        self._clear_url_btn = ctk.CTkButton(
            url_outer,
            text="✕",
            width=40,
            command=self._clear_url,
            **SECONDARY_BTN,
        )
        self._clear_url_btn.grid(row=0, column=2, padx=(0, 8))
        self._enqueue_btn = ctk.CTkButton(
            url_outer,
            text="+ Fila",
            width=72,
            command=self._enqueue_current_url,
            **SECONDARY_BTN,
        )
        self._enqueue_btn.grid(row=0, column=3)

        mid = ctk.CTkFrame(scroll, fg_color="transparent")
        mid.grid(row=2, column=0, padx=cp, pady=(0, SECTION_GAP), sticky="ew")
        mid.grid_columnconfigure(0, weight=1)

        assert self._preview_panel is not None
        preview_card = self._preview_panel.build_into(mid)

        preview_opts = ctk.CTkFrame(preview_card, fg_color="transparent")
        preview_opts.pack(fill="x", padx=12, pady=(0, 14))
        preview_opts.grid_columnconfigure(0, weight=1)

        self._audio_only_var = tk.BooleanVar(value=False)
        self._audio_checkbox = ctk.CTkCheckBox(
            preview_opts,
            text="Somente áudio",
            variable=self._audio_only_var,
            command=self._on_options_changed,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
        )
        self._audio_checkbox.grid(row=0, column=0, sticky="w", pady=(0, 10))
        ctk.CTkLabel(
            preview_opts,
            text="Qualidade",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))
        self._quality_combo = ctk.CTkComboBox(
            preview_opts,
            values=QUALITY_COMBO_VALUES,
            state="readonly",
            command=self._on_quality_changed,
            dropdown_fg_color=APP_BG,
            button_color=BTN_SECONDARY,
            button_hover_color=BTN_SECONDARY_HOVER,
            border_color=ENTRY_STYLE["border_color"],
            fg_color=ENTRY_STYLE["fg_color"],
            text_color=TEXT_PRIMARY,
        )
        self._set_quality_combo(QUALITY_OPTIONS[0])
        self._quality_combo.grid(row=2, column=0, sticky="ew")

        bottom = ctk.CTkFrame(scroll, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=cp, pady=(0, SECTION_GAP), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        log_block = ctk.CTkFrame(bottom, fg_color="transparent")
        log_block.grid(row=0, column=0, sticky="ew")
        log_block.grid_columnconfigure(0, weight=1)
        log_header = ctk.CTkFrame(log_block, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        log_header.grid_columnconfigure(1, weight=1)
        self._log_toggle_btn = ctk.CTkButton(
            log_header, text="▼", width=28, height=24, command=self._toggle_log_panel, **SECONDARY_BTN
        )
        self._log_toggle_btn.grid(row=0, column=0, padx=(0, 6))
        ctk.CTkLabel(
            log_header,
            text="ATIVIDADE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        self._clear_log_btn = ctk.CTkButton(
            log_header, text="Limpar", width=70, height=24, command=self._clear_log, **SECONDARY_BTN
        )
        self._clear_log_btn.grid(row=0, column=2, sticky="e")
        log_card = ctk.CTkFrame(log_block, **CARD_STYLE)
        log_card.grid(row=1, column=0, sticky="ew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(0, weight=1)
        self._log_body = ctk.CTkFrame(log_card, fg_color="transparent")
        self._log_body.grid(row=0, column=0, sticky="nsew")
        self._log_body.grid_columnconfigure(0, weight=1)
        self._log_body.grid_rowconfigure(0, weight=1)
        self._log_box = ctk.CTkTextbox(
            self._log_body,
            state="disabled",
            wrap="word",
            height=LOG_TEXTBOX_HEIGHT,
            fg_color=("#161616", "#161616"),
            border_color=CARD_STYLE["border_color"],
            border_width=1,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family=FONT_BODY[0], size=11),
        )
        self._log_box.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        self._footer = ctk.CTkFrame(self, fg_color="transparent")
        self._footer.grid(row=1, column=0, padx=cp, pady=(8, 16), sticky="ew")
        footer = self._footer
        footer.grid_columnconfigure(0, weight=1)
        self._status_label = ctk.CTkLabel(
            footer,
            text=DEFAULT_STATUS_TEXT,
            anchor="w",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
        )
        self._status_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        self._btn_row.grid(row=1, column=0, sticky="ew")
        self._btn_row.grid_columnconfigure(3, weight=1)
        self._btn_row.bind("<Configure>", self._on_footer_resize)
        btn_row = self._btn_row
        self._open_folder_btn = ctk.CTkButton(
            btn_row,
            text="📁  Abrir pasta",
            width=120,
            height=40,
            command=self._open_folder,
            **SECONDARY_BTN,
        )
        self._open_folder_btn.grid(row=0, column=0, padx=(0, 8))
        self._open_file_btn = ctk.CTkButton(
            btn_row,
            text="📄  Abrir arquivo",
            width=130,
            height=40,
            command=self._open_last_file,
            state="disabled",
            fg_color=BTN_DISABLED,
            hover_color=BTN_SECONDARY,
            text_color=TEXT_PRIMARY,
            corner_radius=6,
        )
        self._open_file_btn.grid(row=0, column=1, padx=(0, 8))
        self._cancel_btn = ctk.CTkButton(
            btn_row,
            text="✕  Cancelar",
            width=120,
            height=40,
            command=self._cancel_download,
            state="disabled",
            fg_color=BTN_DISABLED,
            hover_color=BTN_SECONDARY,
            text_color=TEXT_PRIMARY,
            corner_radius=6,
        )
        self._cancel_btn.grid(row=0, column=2, padx=(0, 8))
        self._download_btn = ctk.CTkButton(
            btn_row,
            text="⬇  Baixar",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_download,
            **PRIMARY_BTN,
        )
        self._download_btn.grid(row=0, column=4, sticky="e")
        self._sync_action_buttons()
        self._on_sync_queue_structure()
        self.after_idle(self._on_view_configure)
        self.after_idle(lambda: self._apply_footer_button_layout(False))

    def _on_view_configure(self, _event: Optional[object] = None) -> None:
        self._sync_scroll_viewport()
        self._on_scroll_wraplength()

    def _sync_scroll_viewport(self) -> None:
        """Keep the scroll area height within the space above the fixed footer."""
        if self._scroll_host is None or self._footer is None:
            return
        try:
            self.update_idletasks()
            total_h = self.winfo_height()
            footer_h = self._footer.winfo_reqheight()
        except tk.TclError:
            return
        total_w = self.winfo_width()
        if total_h <= 1 or total_w <= 1:
            return
        scroll_h = max(160, total_h - footer_h - 4)
        if (
            self._scroll_host.winfo_height() != scroll_h
            or self._scroll_host.winfo_width() != total_w
        ):
            self._scroll_host.configure(height=scroll_h, width=total_w)

    def _on_scroll_wraplength(self) -> None:
        if self._scroll is None:
            return
        if self._preview_panel is not None and self._preview_panel.mid is not None:
            title_lbl = self._preview_panel.preview_title_label
            if title_lbl is not None:
                apply_wraplength_from_widget(
                    title_lbl, self._preview_panel.mid, pad=48, max_px=520
                )

    def _on_footer_resize(self, event: Optional[object] = None) -> None:
        if self._btn_row is None:
            return
        if event is not None and getattr(event, "widget", None) != self._btn_row:
            return
        try:
            width = self._btn_row.winfo_width()
        except tk.TclError:
            return
        if width <= 1:
            return
        narrow = width < DOWNLOADS_FOOTER_STACK_WIDTH
        if narrow == self._footer_layout_narrow:
            return
        self._footer_layout_narrow = narrow
        self._apply_footer_button_layout(narrow)

    def _apply_footer_button_layout(self, narrow: bool) -> None:
        if self._btn_row is None:
            return
        for btn in (
            self._open_folder_btn,
            self._open_file_btn,
            self._cancel_btn,
            self._download_btn,
        ):
            btn.grid_forget()
        if narrow:
            self._btn_row.grid_columnconfigure(3, weight=0)
            self._open_folder_btn.grid(row=0, column=0, padx=(0, 8), sticky="w")
            self._open_file_btn.grid(row=0, column=1, padx=(0, 8), sticky="w")
            self._cancel_btn.grid(row=0, column=2, padx=(0, 8), sticky="w")
            self._download_btn.grid(row=1, column=0, columnspan=3, sticky="e", pady=(8, 0))
        else:
            self._btn_row.grid_columnconfigure(3, weight=1)
            self._open_folder_btn.grid(row=0, column=0, padx=(0, 8))
            self._open_file_btn.grid(row=0, column=1, padx=(0, 8))
            self._cancel_btn.grid(row=0, column=2, padx=(0, 8))
            self._download_btn.grid(row=0, column=4, sticky="e")
        self.after_idle(self._sync_scroll_viewport)

    def _output_dir(self) -> str:
        path = self._get_app_settings().output_dir.strip()
        return path or str(DEFAULT_DOWNLOADS_DIR)

    def _collect_settings(self) -> AppSettings:
        app = self._get_app_settings()
        return AppSettings(
            output_dir=app.output_dir,
            quality=self._get_quality_internal(),
            audio_only=self._audio_only_var.get(),
        )

    def _on_options_changed(self) -> None:
        self._on_audio_toggle()
        self._on_persist_settings()

    def _on_quality_changed(self, _choice: str) -> None:
        self._on_persist_settings()

    def _paste_url(self) -> None:
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return
        if text:
            self._url_entry.delete(0, "end")
            self._url_entry.insert(0, text)
            self._schedule_preview_if_ready()

    def _clear_url(self) -> None:
        self._url_entry.delete(0, "end")
        if not self._is_downloading and self._preview_panel is not None:
            self._preview_panel.clear()

    def _clear_log(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _set_expand_busy(self, busy: bool) -> None:
        self._expanding_playlist = busy
        if busy:
            self._set_download_status("A obter vídeos da playlist…")
            if self._status_reset_after_id is not None:
                self.after_cancel(self._status_reset_after_id)
                self._status_reset_after_id = None
        elif not self._is_downloading:
            self._schedule_status_reset()
        if self._is_downloading:
            return
        state = "disabled" if busy else "normal"
        self._download_btn.configure(state=state)
        self._enqueue_btn.configure(state=state)

    def _resolve_urls_async(
        self,
        url: str,
        playlist_mode: Optional[PlaylistMode],
        on_done: Callable[[Optional[list[str]], Optional[str]], None],
    ) -> None:
        def worker() -> None:
            try:
                urls = resolve_download_urls(url, playlist_mode=playlist_mode)
                self.after(0, lambda: on_done(urls, None))
            except PlaylistExpandError as exc:
                self.after(0, lambda: on_done(None, str(exc)))
            except Exception as exc:
                logger.exception("Falha ao resolver URLs: %s", url[:80])
                self.after(0, lambda: on_done(None, str(exc)))

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
                self.winfo_toplevel(),
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
        self._url_entry.delete(0, "end")
        self._url_entry.insert(0, first)
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
        if enabled:
            self._open_file_btn.configure(state="normal", **SECONDARY_BTN)
        else:
            self._open_file_btn.configure(
                state="disabled",
                fg_color=BTN_DISABLED,
                hover_color=BTN_SECONDARY,
                text_color=TEXT_PRIMARY,
                corner_radius=6,
            )

    def _open_last_file(self) -> None:
        if self._last_download_filepath and os.path.isfile(self._last_download_filepath):
            self._open_path_in_explorer(self._last_download_filepath)

    def _enqueue_current_url(self) -> None:
        if self._is_downloading and self._expanding_playlist:
            return
        url = self._url_entry.get().strip()
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
        if self._audio_only_var.get():
            self._quality_combo.configure(state="disabled")
        else:
            self._quality_combo.configure(state="readonly")

    def _append_log(self, message: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", message + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _set_download_status(self, text: str) -> None:
        self._status_label.configure(text=text)

    def _reset_download_status(self) -> None:
        self._status_reset_after_id = None
        self._set_download_status(DEFAULT_STATUS_TEXT)

    def _schedule_status_reset(self, delay_ms: int = 3000) -> None:
        if self._status_reset_after_id is not None:
            self.after_cancel(self._status_reset_after_id)
        self._status_reset_after_id = self.after(delay_ms, self._reset_download_status)

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
            title = title_lbl.cget("text").strip()
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
        state = "normal" if enabled else "disabled"
        # URL stays editable while downloading so the user can enqueue more links.
        if enabled:
            self._url_entry.configure(state="normal")
            self._clear_url_btn.configure(state="normal")
        self._clear_log_btn.configure(state=state)
        self._open_folder_btn.configure(state=state)
        if not enabled:
            self._open_file_btn.configure(state="disabled")
        else:
            self._update_open_file_button()
        self._audio_checkbox.configure(state=state)
        self._enqueue_btn.configure(state=state)
        if enabled:
            self._on_audio_toggle()
        else:
            self._quality_combo.configure(state="disabled")
        self._download_btn.configure(state=state)
        self._sync_action_buttons()

    def _has_pending_queue(self) -> bool:
        return bool(self._get_queue_snapshot())

    def _sync_action_buttons(self) -> None:
        if self._is_downloading:
            self._cancel_btn.configure(
                text="✕  Cancelar",
                state="normal",
                command=self._cancel_download,
                fg_color=BTN_SECONDARY,
                hover_color=BTN_SECONDARY_HOVER,
            )
        else:
            self._cancel_btn.configure(
                text="Limpar URL",
                state="normal",
                command=self._clear_url,
                fg_color=BTN_SECONDARY,
                hover_color=BTN_SECONDARY_HOVER,
            )

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

        url = self._url_entry.get().strip()
        if not url:
            url = (self._pop_next_queue_url() or "").strip()
            if url:
                self._url_entry.delete(0, "end")
                self._url_entry.insert(0, url)
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
            audio_only=self._audio_only_var.get(),
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
        if self._status_reset_after_id is not None:
            self.after_cancel(self._status_reset_after_id)
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
            self._url_entry.get().strip(),
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
            self._url_entry.get().strip(),
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
                    self._url_entry.focus_set()
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
