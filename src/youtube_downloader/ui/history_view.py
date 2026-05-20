"""Histórico de downloads — lista em cards com thumbnail e canal."""

import os
import webbrowser
from collections.abc import Callable
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk
from PIL import Image

from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    format_file_size,
    format_relative_date,
)
from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import is_youtube_url
from youtube_downloader.ui.theme import (
    CARD_BORDER,
    CARD_STYLE,
    ENTRY_STYLE,
    LINK_BTN,
    SECONDARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    YOUTUBE_BTN,
)

HISTORY_THUMB_SIZE = (128, 72)

logger = get_logger(__name__)


class HistoryView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_open_folder: Callable[[str], None],
        on_open_file: Callable[[str], None],
        on_redownload: Callable[[str, str], None],
        on_remove: Callable[[str], list[DownloadHistoryEntry]],
        on_clear_history: Callable[[], list[DownloadHistoryEntry]],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_open_folder = on_open_folder
        self._on_open_file = on_open_file
        self._on_redownload = on_redownload
        self._on_remove = on_remove
        self._on_clear_history = on_clear_history
        self._entries: list[DownloadHistoryEntry] = []
        self._filter_var = ctk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._on_filter_changed())
        self._thumb_images: list[ctk.CTkImage] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        pad = 24
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=pad, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Histórico",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Downloads concluídos neste aplicativo.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        ctk.CTkButton(
            header,
            text="Limpar histórico",
            width=120,
            command=self._clear_all,
            **SECONDARY_BTN,
        ).grid(row=0, column=1, rowspan=2, padx=(12, 0))

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", padx=pad, pady=(0, 8))
        search_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(
            search_row,
            textvariable=self._filter_var,
            placeholder_text="Filtrar por título ou canal...",
            **ENTRY_STYLE,
        ).grid(row=0, column=0, sticky="ew")

        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._status_label.grid(row=2, column=0, sticky="ew", padx=pad, pady=(0, 8))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=3, column=0, sticky="nsew", padx=pad, pady=(0, 20))
        self._scroll.grid_columnconfigure(0, weight=1)

    @staticmethod
    def _open_url(url: str) -> None:
        cleaned = url.strip()
        if cleaned:
            webbrowser.open(cleaned)

    def _on_filter_changed(self) -> None:
        self._update_status_label()
        self._render_rows()

    def _count_missing_files(self, entries: list[DownloadHistoryEntry]) -> int:
        return sum(1 for e in entries if not os.path.isfile(e.filepath))

    def _filtered_entries(self) -> list[DownloadHistoryEntry]:
        query = self._filter_var.get().strip().casefold()
        if not query:
            return self._entries
        return [
            e
            for e in self._entries
            if query in e.title.casefold() or query in e.channel_name.casefold()
        ]

    def _update_status_label(self) -> None:
        total = len(self._entries)
        visible = self._filtered_entries()
        query = self._filter_var.get().strip()

        if not total:
            self._status_label.configure(text="Nenhum download no histórico.")
            return

        if query:
            text = f"{len(visible)} de {total} itens"
        else:
            text = f"{total} itens no histórico"

        missing = self._count_missing_files(visible if query else self._entries)
        if missing:
            suffix = "arquivo" if missing == 1 else "arquivos"
            text += f" · {missing} {suffix} não encontrado(s) no disco"

        self._status_label.configure(text=text)

    def set_entries(self, entries: list[DownloadHistoryEntry]) -> None:
        self._entries = list(entries)
        self._update_status_label()
        try:
            self._render_rows()
        except Exception:
            logger.exception("Falha ao renderizar lista do historico")
            for child in self._scroll.winfo_children():
                child.destroy()
            ctk.CTkLabel(
                self._scroll,
                text="Não foi possível exibir o histórico. Veja logs/errors.log.",
                font=ctk.CTkFont(size=13),
                text_color=TEXT_MUTED,
                wraplength=520,
                justify="left",
            ).grid(row=0, column=0, pady=32, padx=8, sticky="w")

    def _load_thumbnail(self, thumbnail_path: str) -> Optional[ctk.CTkImage]:
        if not thumbnail_path or not os.path.isfile(thumbnail_path):
            return None
        try:
            img = Image.open(thumbnail_path).convert("RGB")
            img = img.resize(HISTORY_THUMB_SIZE, Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=HISTORY_THUMB_SIZE,
            )
            self._thumb_images.append(ctk_img)
            return ctk_img
        except OSError:
            return None

    def _render_rows(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        self._thumb_images.clear()

        visible = self._filtered_entries()
        if not visible:
            if not self._entries:
                msg = (
                    "Nenhum download no histórico. "
                    "Conclua um download na tela Downloads."
                )
            else:
                msg = "Nenhum resultado para este filtro."
            ctk.CTkLabel(
                self._scroll,
                text=msg,
                font=ctk.CTkFont(size=13),
                text_color=TEXT_MUTED,
                wraplength=520,
                justify="left",
            ).grid(row=0, column=0, pady=32, padx=8, sticky="w")
            return

        for idx, entry in enumerate(visible):
            self._add_card(idx, entry)

    def _add_thumb_placeholder(self, parent: ctk.CTkFrame, is_audio: bool) -> None:
        icon = "♪" if is_audio else "▶"
        box = ctk.CTkFrame(
            parent,
            width=HISTORY_THUMB_SIZE[0],
            height=HISTORY_THUMB_SIZE[1],
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            corner_radius=6,
        )
        box.pack()
        box.pack_propagate(False)
        ctk.CTkLabel(
            box,
            text=icon,
            font=ctk.CTkFont(size=22),
            text_color=TEXT_SECONDARY,
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _add_card(self, idx: int, entry: DownloadHistoryEntry) -> None:
        path = entry.filepath
        file_exists = os.path.isfile(path)

        card = ctk.CTkFrame(self._scroll, **CARD_STYLE)
        card.grid(row=idx, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(1, weight=1)

        thumb_col = ctk.CTkFrame(card, fg_color="transparent")
        thumb_col.grid(row=0, column=0, rowspan=2, padx=(12, 10), pady=10, sticky="n")

        thumb_image = self._load_thumbnail(entry.thumbnail_path)
        if thumb_image:
            ctk.CTkLabel(
                thumb_col,
                text="",
                image=thumb_image,
                width=HISTORY_THUMB_SIZE[0],
                height=HISTORY_THUMB_SIZE[1],
            ).pack()
        else:
            self._add_thumb_placeholder(thumb_col, entry.is_audio)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=0, column=1, sticky="ew", pady=(10, 0))
        ctk.CTkLabel(
            body,
            text=entry.title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        channel = entry.channel_name.strip()
        channel_url = entry.channel_url.strip()
        if channel and channel_url:
            ctk.CTkButton(
                body,
                text=channel,
                font=ctk.CTkFont(size=12, underline=True),
                anchor="w",
                command=lambda u=channel_url: self._open_url(u),
                **LINK_BTN,
            ).pack(anchor="w", pady=(2, 0), fill="x")
        elif channel:
            ctk.CTkLabel(
                body,
                text=channel,
                font=ctk.CTkFont(size=12),
                text_color=TEXT_SECONDARY,
                anchor="w",
            ).pack(anchor="w", pady=(2, 0))

        size_label = format_file_size(entry.size_bytes) if file_exists else "—"
        meta = (
            f"{format_relative_date(entry.completed_at)} · "
            f"{entry.format_ext} · {size_label}"
        )
        ctk.CTkLabel(
            body,
            text=meta,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        if not file_exists:
            ctk.CTkLabel(
                body,
                text="Arquivo não encontrado",
                font=ctk.CTkFont(size=11),
                text_color=TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w", pady=(2, 0))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=1, column=1, sticky="w", pady=(0, 10))

        video_url = entry.source_url.strip()
        yt_state = "normal" if video_url and is_youtube_url(video_url) else "disabled"
        ctk.CTkButton(
            actions,
            text="▶",
            command=lambda u=video_url: self._open_url(u),
            state=yt_state,
            **YOUTUBE_BTN,
        ).pack(side="left", padx=(0, 6))

        open_state = "normal" if file_exists else "disabled"
        ctk.CTkButton(
            actions,
            text="Abrir",
            width=72,
            state=open_state,
            command=lambda p=path: self._on_open_file(p),
            **SECONDARY_BTN,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Pasta",
            width=72,
            command=lambda p=path: self._on_open_folder(p),
            **SECONDARY_BTN,
        ).pack(side="left", padx=(0, 6))

        redo_state = "normal" if entry.source_url.strip() else "disabled"
        ctk.CTkButton(
            actions,
            text="Baixar de novo",
            width=110,
            state=redo_state,
            command=lambda u=entry.source_url, t=entry.title: self._on_redownload(u, t),
            **SECONDARY_BTN,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Remover",
            width=80,
            command=lambda p=path: self._remove_entry(p),
            **SECONDARY_BTN,
        ).pack(side="left")

    def _remove_entry(self, filepath: str) -> None:
        if not messagebox.askyesno(
            "Remover do histórico",
            "Remover este item do histórico?\nO arquivo no disco não será apagado.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.set_entries(self._on_remove(filepath))

    def _clear_all(self) -> None:
        if not self._entries:
            return
        if not messagebox.askyesno(
            "Limpar histórico",
            "Limpar todo o histórico?\nOs arquivos no disco não serão apagados.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.set_entries(self._on_clear_history())
