"""Main application window."""

import io
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk
from PIL import Image

from youtube_downloader.config import (
    APP_TITLE,
    APP_VERSION,
    DEFAULT_DOWNLOADS_DIR,
    QUALITY_COMBO_VALUES,
    QUALITY_DISPLAY_LABELS,
    QUALITY_FROM_DISPLAY,
    QUALITY_OPTIONS,
    WINDOW_SIZE,
)
from youtube_downloader.ui.nav_sidebar import NavSidebar
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
    FONT_SECTION,
    FONT_TITLE,
    GHOST_BTN,
    ICON_BTN,
    PRIMARY_BTN,
    SECONDARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    add_history_entry,
    load_history,
)
from youtube_downloader.core.downloader import YoutubeDownloader
from youtube_downloader.core.ffmpeg_utils import is_bundled_ffmpeg
from youtube_downloader.core.logging_config import (
    LOG_CACHE_DIR,
    LOG_DIR,
    clear_preview_cache,
    get_logger,
)
from youtube_downloader.core.metadata import (
    VideoPreview,
    fetch_preview,
    format_duration,
    is_youtube_url,
)
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.settings import AppSettings, load_settings, save_settings
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui.history_view import HistoryView
from youtube_downloader.ui.settings_view import SettingsView

logger = get_logger("app")

PREVIEW_DEBOUNCE_MS = 600
THUMB_DISPLAY_SIZE = (240, 135)
STATUS_WRAPLENGTH = 680
SECTION_PADX = 24
SECTION_GAP = 10
DEFAULT_STATUS_TEXT = "Pronto para baixar."


class YoutubeDownloaderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(820, 600)
        self.configure(fg_color=APP_BG)

        self._view_frames: dict[str, ctk.CTkFrame] = {}
        self._sidebar: Optional[NavSidebar] = None
        self._log_body: Optional[ctk.CTkFrame] = None
        self._log_expanded = True
        self._history_entries: list[DownloadHistoryEntry] = load_history()
        self._history_view: Optional[HistoryView] = None

        self._downloader = YoutubeDownloader()
        self._event_queue: queue.Queue[ProgressEvent] = queue.Queue()
        self._download_thread: Optional[object] = None
        self._is_downloading = False
        self._output_dir = tk.StringVar(value=str(DEFAULT_DOWNLOADS_DIR))
        self._preview_after_id: Optional[str] = None
        self._preview_request_id = 0
        self._ctk_preview_image: Optional[ctk.CTkImage] = None
        self._preview_pil_light: Optional[Image.Image] = None
        self._preview_pil_dark: Optional[Image.Image] = None
        self._placeholder_image: Optional[ctk.CTkImage] = None
        self._placeholder_pil_light: Optional[Image.Image] = None
        self._placeholder_pil_dark: Optional[Image.Image] = None
        self._status_reset_after_id: Optional[str] = None
        self._last_download_filepath: Optional[str] = None
        self._settings = load_settings()
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

    def _make_section(
        self, parent: ctk.CTkBaseClass, title: str, *, uppercase: bool = False
    ) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        """Section title + card frame; returns (section_container, card)."""
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.grid_columnconfigure(0, weight=1)
        label_text = title.upper() if uppercase else title
        ctk.CTkLabel(
            section,
            text=label_text,
            anchor="w",
            font=ctk.CTkFont(family=FONT_SECTION[0], size=FONT_SECTION[1], weight="bold"),
            text_color=TEXT_SECONDARY if uppercase else TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        card = ctk.CTkFrame(section, **CARD_STYLE)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        return section, card

    def _get_quality_internal(self) -> str:
        display = self._quality_combo.get()
        return QUALITY_FROM_DISPLAY.get(display, QUALITY_OPTIONS[0])

    def _set_quality_combo(self, quality: str) -> None:
        label = QUALITY_DISPLAY_LABELS.get(quality, QUALITY_DISPLAY_LABELS[QUALITY_OPTIONS[0]])
        self._quality_combo.set(label)

    def _update_progress_percent(self, percent: Optional[float]) -> None:
        if percent is None:
            self._progress_pct_label.configure(text="0%")
        else:
            self._progress_pct_label.configure(text=f"{min(percent, 1.0) * 100:.0f}%")

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
            actions, text="⚙", command=self._show_preferences, **ICON_BTN
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

    def _build_placeholder_view(
        self, parent: ctk.CTkFrame, view_id: str, title: str, message: str
    ) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._view_frames[view_id] = frame
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(4, 8))
        ctk.CTkLabel(
            frame,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="nw",
            justify="left",
            wraplength=520,
        ).grid(row=1, column=0, sticky="nw", padx=4, pady=(0, 8))

    def _add_history_entry(self, filepath: str, title: Optional[str] = None) -> None:
        if not os.path.isfile(filepath):
            return
        label = (title or "").strip() or os.path.basename(filepath)
        entry = DownloadHistoryEntry.from_filepath(filepath, label)
        self._history_entries = add_history_entry(entry)
        if self._history_view is not None:
            self._history_view.set_entries(self._history_entries)

    def _open_history_item(self, filepath: str) -> None:
        if os.path.isfile(filepath):
            folder = os.path.dirname(filepath)
            if os.path.isdir(folder):
                self._open_path_in_explorer(folder)
                return
        if os.path.isdir(filepath):
            self._open_path_in_explorer(filepath)

    def _show_preview_panel(self, visible: bool) -> None:
        if visible:
            self._preview_frame.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
            self._preview_placeholder.grid_remove()
        else:
            self._preview_frame.grid_remove()
            self._preview_placeholder.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

    def _build_download_view(self, parent: ctk.CTkFrame) -> None:
        page = ctk.CTkFrame(parent, fg_color="transparent")
        self._view_frames["download"] = page
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(3, weight=1)
        cp = 20

        ctk.CTkLabel(
            page,
            text="URL do YouTube",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=cp, pady=(4, 6), sticky="ew")

        url_outer = ctk.CTkFrame(page, fg_color="transparent")
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
        self._url_entry.grid(row=0, column=1, sticky="ew")
        self._url_entry.bind("<<Paste>>", lambda _e: self._schedule_preview())
        self._url_entry.bind("<KeyRelease>", lambda _e: self._schedule_preview())

        mid = ctk.CTkFrame(page, fg_color="transparent")
        mid.grid(row=2, column=0, padx=cp, pady=(0, SECTION_GAP), sticky="nsew")
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)
        mid.grid_rowconfigure(0, weight=1)

        self._preview_placeholder = ctk.CTkFrame(mid, **CARD_STYLE)
        self._preview_placeholder.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        ctk.CTkLabel(
            self._preview_placeholder,
            text="O preview do vídeo aparecerá aqui",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=12),
        ).place(relx=0.5, rely=0.5, anchor="center")

        self._preview_frame = ctk.CTkFrame(mid, **CARD_STYLE)
        self._preview_frame.grid_remove()
        self._preview_frame.grid_columnconfigure(0, weight=1)

        thumb_wrap = ctk.CTkFrame(self._preview_frame, fg_color="transparent")
        thumb_wrap.pack(fill="x", padx=12, pady=(12, 8))
        self._thumb_label = ctk.CTkLabel(
            thumb_wrap,
            text="",
            width=THUMB_DISPLAY_SIZE[0],
            height=THUMB_DISPLAY_SIZE[1],
            fg_color=("#2a2a2a", "#2a2a2a"),
            corner_radius=6,
        )
        self._thumb_label.pack(anchor="w")
        self._ensure_placeholder_image()
        self._thumb_duration_label = ctk.CTkLabel(
            thumb_wrap,
            text="",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=("#000000", "#000000"),
            corner_radius=4,
            width=44,
            height=20,
        )
        self._thumb_duration_label.place(
            x=THUMB_DISPLAY_SIZE[0] - 52, y=THUMB_DISPLAY_SIZE[1] - 28
        )
        self._preview_title_label = ctk.CTkLabel(
            self._preview_frame,
            text="",
            anchor="w",
            justify="left",
            wraplength=320,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        self._preview_title_label.pack(fill="x", padx=12, pady=(0, 4))
        self._preview_subtitle_label = ctk.CTkLabel(
            self._preview_frame,
            text="",
            anchor="w",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
        )
        self._preview_subtitle_label.pack(fill="x", padx=12, pady=(0, 12))

        opts_card = ctk.CTkFrame(mid, **CARD_STYLE)
        opts_card.grid(row=0, column=1, sticky="nsew")
        opts_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            opts_card,
            text="Opções",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 8), sticky="w")
        self._audio_only_var = tk.BooleanVar(value=False)
        self._audio_checkbox = ctk.CTkCheckBox(
            opts_card,
            text="Somente áudio",
            variable=self._audio_only_var,
            command=self._on_options_changed,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
        )
        self._audio_checkbox.grid(row=1, column=0, padx=14, pady=4, sticky="w")
        self._playlist_var = tk.BooleanVar(value=False)
        self._playlist_checkbox = ctk.CTkCheckBox(
            opts_card,
            text="Baixar playlist",
            variable=self._playlist_var,
            command=self._on_options_changed,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
        )
        self._playlist_checkbox.grid(row=2, column=0, padx=14, pady=4, sticky="w")
        ctk.CTkLabel(
            opts_card,
            text="Qualidade",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=3, column=0, padx=14, pady=(12, 6), sticky="w")
        self._quality_combo = ctk.CTkComboBox(
            opts_card,
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
        self._quality_combo.grid(row=4, column=0, padx=14, pady=(0, 14), sticky="ew")

        bottom = ctk.CTkFrame(page, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=cp, pady=(0, SECTION_GAP), sticky="nsew")
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        dest_block = ctk.CTkFrame(bottom, fg_color="transparent")
        dest_block.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        dest_block.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            dest_block,
            text="Pasta de Destino",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        dest_card = ctk.CTkFrame(dest_block, **CARD_STYLE)
        dest_card.grid(row=1, column=0, sticky="nsew")
        dest_card.grid_columnconfigure(0, weight=1)
        path_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        path_row.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        path_row.grid_columnconfigure(0, weight=1)
        self._folder_entry = ctk.CTkEntry(
            path_row, textvariable=self._output_dir, state="readonly", **ENTRY_STYLE
        )
        self._folder_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self._browse_btn = ctk.CTkButton(
            path_row, text="📁", width=40, command=self._browse_folder, **SECONDARY_BTN
        )
        self._browse_btn.grid(row=0, column=1)

        log_block = ctk.CTkFrame(bottom, fg_color="transparent")
        log_block.grid(row=0, column=1, sticky="nsew")
        log_block.grid_columnconfigure(0, weight=1)
        log_block.grid_rowconfigure(1, weight=1)
        log_header = ctk.CTkFrame(log_block, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        log_header.grid_columnconfigure(1, weight=1)
        self._log_toggle_btn = ctk.CTkButton(
            log_header, text="▼", width=28, height=24, command=self._toggle_log_panel, **SECONDARY_BTN
        )
        self._log_toggle_btn.grid(row=0, column=0, padx=(0, 6))
        ctk.CTkLabel(
            log_header,
            text="ATIVIDADE (LOG)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        self._clear_log_btn = ctk.CTkButton(
            log_header, text="Limpar", width=70, height=24, command=self._clear_log, **SECONDARY_BTN
        )
        self._clear_log_btn.grid(row=0, column=2, sticky="e")
        log_card = ctk.CTkFrame(log_block, **CARD_STYLE)
        log_card.grid(row=1, column=0, sticky="nsew")
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
            height=100,
            fg_color=("#161616", "#161616"),
            border_color=CARD_STYLE["border_color"],
            border_width=1,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family=FONT_BODY[0], size=11),
        )
        self._log_box.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        footer = ctk.CTkFrame(page, fg_color="transparent")
        footer.grid(row=4, column=0, padx=cp, pady=(0, 16), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        status_row = ctk.CTkFrame(footer, fg_color="transparent")
        status_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        status_row.grid_columnconfigure(0, weight=1)
        self._status_label = ctk.CTkLabel(
            status_row,
            text=DEFAULT_STATUS_TEXT,
            anchor="w",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
        )
        self._status_label.grid(row=0, column=0, sticky="w")
        self._progress_pct_label = ctk.CTkLabel(
            status_row,
            text="0%",
            anchor="e",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
        )
        self._progress_pct_label.grid(row=0, column=1, sticky="e")
        self._progress_bar = ctk.CTkProgressBar(
            footer, height=6, progress_color=ACCENT, fg_color=("#2a2a2a", "#2a2a2a")
        )
        self._progress_bar.set(0)
        self._progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self._playlist_progress_label = ctk.CTkLabel(
            footer, text="", anchor="w", text_color=TEXT_MUTED, font=ctk.CTkFont(size=11)
        )
        self._playlist_progress_label.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="e")
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
        self._cancel_btn.grid(row=0, column=0, padx=(0, 8))
        self._download_btn = ctk.CTkButton(
            btn_row,
            text="⬇  Baixar",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_download,
            **PRIMARY_BTN,
        )
        self._download_btn.grid(row=0, column=1)

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

        self._build_download_view(content)
        self._build_placeholder_view(
            content,
            "library",
            "Biblioteca",
            "Sua biblioteca de vídeos baixados aparecerá aqui em uma versão futura.\n"
            "Por enquanto, use a pasta de destino configurada em Configurações.",
        )
        self._settings_view = SettingsView(content, on_save=self._on_settings_saved)
        self._view_frames["settings"] = self._settings_view
        self._settings_view.load_settings(self._settings)
        self._history_view = HistoryView(content, on_open_path=self._open_history_item)
        self._view_frames["history"] = self._history_view
        self._history_view.set_entries(self._history_entries)

        self._switch_view("download")

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-v>", self._on_ctrl_v)
        self.bind_all("<Control-comma>", self._on_ctrl_preferences)

    def _on_ctrl_v(self, _event: Optional[object] = None) -> None:
        if not self._is_downloading:
            self._paste_url()

    def _on_ctrl_preferences(self, _event: Optional[object] = None) -> None:
        self._show_preferences()

    def _show_preferences(self) -> None:
        if self._is_downloading:
            return
        self._switch_view("settings")
        if self._sidebar:
            self._sidebar.set_active("settings")
        if self._settings_view is not None:
            self._settings_view.load_settings(self._settings)

    def _on_settings_saved(self, settings: AppSettings) -> None:
        if self._is_downloading:
            return
        self._settings = settings
        save_settings(settings)
        self._apply_settings(settings)

    def _show_temporary_status(self, message: str, delay_ms: int = 8000) -> None:
        if self._ffmpeg_status_after_id is not None:
            self.after_cancel(self._ffmpeg_status_after_id)
        self._set_download_status(message)
        self._ffmpeg_status_after_id = self.after(
            delay_ms, self._clear_temporary_status
        )

    def _clear_temporary_status(self) -> None:
        self._ffmpeg_status_after_id = None
        if not self._is_downloading:
            self._set_download_status(DEFAULT_STATUS_TEXT)

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

    def _schedule_preview(self) -> None:
        if self._is_downloading:
            return
        if self._preview_after_id is not None:
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(PREVIEW_DEBOUNCE_MS, self._run_preview_fetch)

    def _run_preview_fetch(self) -> None:
        self._preview_after_id = None
        if self._is_downloading:
            return

        url = self._url_entry.get().strip()
        if not url or not is_youtube_url(url):
            logger.debug("preview ignorado: URL vazia ou não-YouTube")
            self._clear_preview()
            return

        self._preview_request_id += 1
        request_id = self._preview_request_id
        logger.debug("preview agendado request_id=%s url=%s", request_id, url)
        self._show_preview_loading()

        def worker() -> None:
            logger.debug("preview fetch iniciado request_id=%s", request_id)
            preview = fetch_preview(url)
            logger.debug(
                "preview fetch fim request_id=%s erro=%s thumb=%s",
                request_id,
                bool(preview.error),
                len(preview.thumbnail_bytes) if preview.thumbnail_bytes else 0,
            )
            self._event_queue.put(
                ProgressEvent(
                    event_type=EventType.PREVIEW_READY,
                    preview=preview,
                    preview_url=url,
                    preview_request_id=request_id,
                )
            )

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_placeholder_image(self) -> ctk.CTkImage:
        if self._placeholder_image is not None:
            return self._placeholder_image
        gray = Image.new("RGB", THUMB_DISPLAY_SIZE, (64, 64, 64))
        self._placeholder_pil_light = gray.copy()
        self._placeholder_pil_dark = gray.copy()
        self._placeholder_image = ctk.CTkImage(
            light_image=self._placeholder_pil_light,
            dark_image=self._placeholder_pil_dark,
            size=THUMB_DISPLAY_SIZE,
        )
        return self._placeholder_image

    def _configure_thumb(self, image: Optional[ctk.CTkImage], text: str) -> None:
        """Always attach a valid CTkImage (never None) to avoid Tcl pyimage errors."""
        self._thumb_label.configure(
            image=image if image is not None else self._ensure_placeholder_image(),
            text=text,
        )

    def _release_preview_images(self) -> None:
        self._ctk_preview_image = None
        self._preview_pil_light = None
        self._preview_pil_dark = None

    def _detach_thumb_image(self) -> None:
        """Point label at placeholder before GC of the previous CTkImage."""
        self._configure_thumb(None, "")
        self._release_preview_images()

    @staticmethod
    def _pil_rgb_from_bytes(data: bytes) -> Image.Image:
        base = Image.open(io.BytesIO(data))
        if base.mode == "RGBA":
            background = Image.new("RGB", base.size, (40, 40, 40))
            background.paste(base, mask=base.split()[3])
            return background
        return base.convert("RGB")

    def _show_preview_loading(self) -> None:
        clear_preview_cache()
        self._show_preview_panel(True)
        self._detach_thumb_image()
        self._configure_thumb(None, "…")
        self._preview_title_label.configure(text="Carregando preview…")
        self._preview_subtitle_label.configure(text="")

    def _clear_preview(self) -> None:
        self._preview_request_id += 1
        clear_preview_cache()
        self._detach_thumb_image()
        self._configure_thumb(None, "")
        self._preview_title_label.configure(text="")
        self._preview_subtitle_label.configure(text="")
        self._thumb_duration_label.configure(text="")
        self._show_preview_panel(False)

    def _apply_preview(
        self,
        preview: VideoPreview,
        url: str,
        request_id: Optional[int] = None,
    ) -> None:
        if request_id is not None and request_id != self._preview_request_id:
            logger.warning(
                "preview obsoleto ignorado: request_id=%s atual=%s",
                request_id,
                self._preview_request_id,
            )
            return
        if self._url_entry.get().strip() != url:
            logger.warning(
                "preview URL divergente ignorado: esperado=%r campo=%r",
                url,
                self._url_entry.get().strip(),
            )
            return
        if self._is_downloading:
            return

        logger.debug(
            "apply_preview request_id=%s title=%r bytes=%s",
            request_id,
            preview.title[:50] if preview.title else "",
            len(preview.thumbnail_bytes) if preview.thumbnail_bytes else 0,
        )

        if preview.error:
            logger.error("preview erro: %s | url=%s", preview.error, url)
            self._show_preview_panel(True)
            self._detach_thumb_image()
            self._configure_thumb(None, "?")
            self._preview_title_label.configure(text="Preview indisponível")
            self._preview_subtitle_label.configure(text=preview.error[:120])
            return

        self._show_preview_panel(True)
        self._preview_title_label.configure(text=preview.title)

        if preview.is_playlist and preview.playlist_count is not None:
            self._preview_subtitle_label.configure(
                text=f"Playlist · {preview.playlist_count} vídeos"
            )
        else:
            channel = preview.uploader or "Canal"
            duration = format_duration(preview.duration_seconds)
            self._preview_subtitle_label.configure(
                text=f"{channel} · {duration}" if duration else channel
            )

        duration_text = format_duration(preview.duration_seconds)
        if duration_text:
            self._thumb_duration_label.configure(text=duration_text)
        else:
            self._thumb_duration_label.configure(text="")

        if preview.thumbnail_bytes:
            try:
                cache_id = request_id if request_id is not None else self._preview_request_id
                cache_path = LOG_CACHE_DIR / f"preview_{cache_id}.jpg"
                base = self._pil_rgb_from_bytes(preview.thumbnail_bytes)
                base.save(cache_path, "JPEG", quality=90)

                self._preview_pil_light = base.copy()
                self._preview_pil_dark = base.copy()
                self._ctk_preview_image = ctk.CTkImage(
                    light_image=self._preview_pil_light,
                    dark_image=self._preview_pil_dark,
                    size=THUMB_DISPLAY_SIZE,
                )
                self._configure_thumb(self._ctk_preview_image, "")
                logger.debug(
                    "thumbnail exibida request_id=%s cache=%s size=%s",
                    cache_id,
                    cache_path,
                    base.size,
                )
            except Exception:
                logger.exception(
                    "Falha ao exibir thumbnail request_id=%s url=%s",
                    request_id,
                    url,
                )
                self._detach_thumb_image()
                self._configure_thumb(None, "?")
        else:
            logger.warning("preview sem thumbnail_bytes request_id=%s url=%s", request_id, url)
            self._detach_thumb_image()
            self._configure_thumb(None, "?")

    def _collect_settings(self) -> AppSettings:
        return AppSettings(
            output_dir=self._output_dir.get().strip() or str(DEFAULT_DOWNLOADS_DIR),
            quality=self._get_quality_internal(),
            audio_only=self._audio_only_var.get(),
            download_playlist=self._playlist_var.get(),
        )

    def _apply_settings(self, settings: AppSettings) -> None:
        self._output_dir.set(settings.output_dir)
        if settings.quality in QUALITY_OPTIONS:
            self._set_quality_combo(settings.quality)
        self._audio_only_var.set(settings.audio_only)
        self._playlist_var.set(settings.download_playlist)
        self._on_audio_toggle()
        if self._settings_view is not None:
            self._settings_view.load_settings(settings)

    def _persist_settings(self) -> None:
        save_settings(self._collect_settings())

    def _on_close(self) -> None:
        self._persist_settings()
        self.destroy()

    def _on_options_changed(self) -> None:
        self._on_audio_toggle()
        self._persist_settings()

    def _on_quality_changed(self, _choice: str) -> None:
        self._persist_settings()

    def _paste_url(self) -> None:
        if self._is_downloading:
            return
        try:
            text = self.clipboard_get().strip()
        except tk.TclError:
            return
        if text:
            self._url_entry.delete(0, "end")
            self._url_entry.insert(0, text)
            self._schedule_preview()

    def _clear_url(self) -> None:
        if self._is_downloading:
            return
        self._url_entry.delete(0, "end")
        self._clear_preview()

    def _clear_log(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _update_playlist_progress_label(
        self,
        completed: Optional[int],
        total: Optional[int],
    ) -> None:
        if total is not None and total >= 2 and completed is not None:
            self._playlist_progress_label.configure(
                text=f"Playlist: {completed}/{total} concluídos"
            )
        else:
            self._playlist_progress_label.configure(text="")

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
        dialog.geometry("440x260")
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

        ctk.CTkButton(
            dialog,
            text="OK",
            width=120,
            command=dialog.destroy,
            **PRIMARY_BTN,
        ).pack(pady=(20, 20))

    def _open_last_file(self) -> None:
        if self._last_download_filepath and os.path.isfile(self._last_download_filepath):
            self._open_path_in_explorer(self._last_download_filepath)

    def _browse_folder(self) -> None:
        if self._is_downloading:
            return
        initial = self._output_dir.get().strip() or str(DEFAULT_DOWNLOADS_DIR)
        folder = filedialog.askdirectory(
            title="Escolher pasta de destino",
            initialdir=initial if os.path.isdir(initial) else str(DEFAULT_DOWNLOADS_DIR),
        )
        if folder:
            self._output_dir.set(folder)
            self._persist_settings()

    def _open_path_in_explorer(self, path: str) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except OSError as exc:
            logger.exception("Falha ao abrir pasta: %s", path)
            self._append_log(f"Erro ao abrir pasta: {exc}")

    def _open_logs(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._open_path_in_explorer(str(LOG_DIR))

    def _open_folder(self) -> None:
        output_dir = self._output_dir.get().strip() or str(DEFAULT_DOWNLOADS_DIR)
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

    def _get_preview_title_for_log(self) -> Optional[str]:
        title = self._preview_title_label.cget("text").strip()
        if not title or title in ("Carregando preview…", "—"):
            return None
        return title

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._url_entry.configure(state=state)
        self._browse_btn.configure(state=state)
        self._clear_log_btn.configure(state=state)
        self._audio_checkbox.configure(state=state)
        self._playlist_checkbox.configure(state=state)
        if enabled:
            self._on_audio_toggle()
        else:
            self._quality_combo.configure(state="disabled")
        self._download_btn.configure(state=state)
        self._cancel_btn.configure(state="disabled" if enabled else "normal")

    def _start_download(self) -> None:
        if self._is_downloading:
            return

        url = self._url_entry.get().strip()
        output_dir = self._output_dir.get().strip()

        if not url:
            logger.warning("Download bloqueado: URL vazia")
            self._append_log("Erro: informe a URL do vídeo ou playlist.")
            return
        if not output_dir:
            output_dir = str(DEFAULT_DOWNLOADS_DIR)
            self._output_dir.set(output_dir)
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as exc:
                logger.error("Download bloqueado: pasta invalida %s (%s)", output_dir, exc)
                self._append_log(f"Erro: não foi possível criar a pasta de destino: {exc}")
                return

        job = DownloadJob(
            url=url,
            output_dir=output_dir,
            quality=self._get_quality_internal(),
            audio_only=self._audio_only_var.get(),
            download_playlist=self._playlist_var.get(),
        )
        self._persist_settings()

        self._is_downloading = True
        self._update_playlist_progress_label(0, None)
        if self._preview_after_id is not None:
            self.after_cancel(self._preview_after_id)
            self._preview_after_id = None
        self._set_controls_enabled(False)
        self._progress_bar.set(0)
        self._update_progress_percent(0)
        if self._status_reset_after_id is not None:
            self.after_cancel(self._status_reset_after_id)
            self._status_reset_after_id = None
        start_label = self._get_preview_title_for_log() or truncate_text(url, 60)
        self._append_log(f"Iniciando download: {start_label}")
        self._set_download_status("Baixando…")

        def worker() -> None:
            def on_event(event: ProgressEvent) -> None:
                self._event_queue.put(event)

            self._downloader.download(job, on_event)

        self._download_thread = threading.Thread(target=worker, daemon=True)
        self._download_thread.start()

    def _cancel_download(self) -> None:
        if self._is_downloading:
            logger.info(
                "Usuario cancelou download: %s",
                self._url_entry.get().strip(),
            )
            self._downloader.cancel()
            self._set_download_status("Cancelando…")
            self._append_log("Cancelando download...")

    def _poll_queue(self) -> None:
        while True:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
        self.after(50, self._poll_queue)

    def _handle_event(self, event: ProgressEvent) -> None:
        if event.event_type == EventType.PREVIEW_READY:
            if event.preview is not None and event.preview_url:
                self._apply_preview(
                    event.preview,
                    event.preview_url,
                    request_id=event.preview_request_id,
                )
            return

        if event.event_type == EventType.PREVIEW_CLEAR:
            self._clear_preview()
            return

        if event.event_type == EventType.PROGRESS:
            if event.percent is not None:
                self._progress_bar.set(event.percent)
                self._update_progress_percent(event.percent)
            if event.message:
                self._set_download_status(event.message)
            self._update_playlist_progress_label(
                event.playlist_completed,
                event.playlist_total,
            )

        elif event.event_type == EventType.LOG:
            self._append_log(event.message)
            if event.percent is not None:
                self._progress_bar.set(event.percent)
                self._update_progress_percent(event.percent)
            self._set_download_status(event.message)
            self._update_playlist_progress_label(
                event.playlist_completed,
                event.playlist_total,
            )

        elif event.event_type in (
            EventType.DONE,
            EventType.ERROR,
            EventType.CANCELLED,
        ):
            if event.percent is not None:
                self._progress_bar.set(event.percent)
                self._update_progress_percent(event.percent)
            elif event.event_type == EventType.DONE:
                self._progress_bar.set(1.0)
                self._update_progress_percent(1.0)
            self._append_log(event.message)
            if event.event_type == EventType.DONE:
                self._set_download_status("Download concluído.")
                if event.filepath and os.path.isfile(event.filepath):
                    self._last_download_filepath = event.filepath
                    self._add_history_entry(
                        event.filepath,
                        title=self._get_preview_title_for_log(),
                    )
                self._update_playlist_progress_label(
                    event.playlist_completed,
                    event.playlist_total,
                )
            elif event.event_type == EventType.ERROR:
                self._set_download_status("Erro no download.")
                self._update_playlist_progress_label(None, None)
            else:
                self._set_download_status("Download cancelado.")
                self._update_playlist_progress_label(None, None)
            self._is_downloading = False
            self._set_controls_enabled(True)
            self._schedule_status_reset()


def run() -> None:
    from youtube_downloader.core.logging_config import install_exception_hooks, setup_logging

    setup_logging()
    install_exception_hooks()
    logger.info("Aplicativo iniciado")
    app = YoutubeDownloaderApp()
    app.mainloop()
