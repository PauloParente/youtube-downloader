"""Histórico de downloads — layout em tabela conforme mockup."""

import os
from collections.abc import Callable

import customtkinter as ctk

from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    format_file_size,
    format_relative_date,
)
from youtube_downloader.ui.theme import (
    CARD_BORDER,
    CARD_STYLE,
    ENTRY_STYLE,
    SECONDARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class HistoryView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_open_folder: Callable[[str], None],
        on_open_file: Callable[[str], None],
        on_redownload: Callable[[str, str], None],
        on_remove: Callable[[str], list[DownloadHistoryEntry]],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_open_folder = on_open_folder
        self._on_open_file = on_open_file
        self._on_redownload = on_redownload
        self._on_remove = on_remove
        self._entries: list[DownloadHistoryEntry] = []
        self._filter_var = ctk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._render_rows())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        pad = 24
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=pad, pady=(20, 16))
        header.grid_columnconfigure(0, weight=1)

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.grid(row=0, column=0, sticky="nw")
        ctk.CTkLabel(
            title_col,
            text="Histórico",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text="Gerencie e acesse seus downloads concluídos recentemente.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w",
            wraplength=480,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        search_wrap = ctk.CTkFrame(header, fg_color="transparent")
        search_wrap.grid(row=0, column=1, sticky="e", padx=(16, 0))
        search_inner = ctk.CTkFrame(search_wrap, fg_color="transparent")
        search_inner.pack()
        ctk.CTkLabel(
            search_inner,
            text="🔍",
            width=24,
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(8, 0))
        self._search_entry = ctk.CTkEntry(
            search_inner,
            textvariable=self._filter_var,
            width=220,
            placeholder_text="Filtrar histórico...",
            **ENTRY_STYLE,
        )
        self._search_entry.pack(side="left", padx=(4, 8), pady=6)

        self._table_card = ctk.CTkFrame(self, **CARD_STYLE)
        self._table_card.grid(row=2, column=0, sticky="nsew", padx=pad, pady=(0, 24))
        self._table_card.grid_columnconfigure(0, weight=1)
        self._table_card.grid_rowconfigure(1, weight=1)

        cols = ctk.CTkFrame(self._table_card, fg_color="transparent")
        cols.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        cols.grid_columnconfigure(1, weight=1)
        for col, (text, sticky, padx) in enumerate(
            (
                ("", "w", (0, 0)),
                ("NOME DO VÍDEO", "w", (0, 0)),
                ("DATA", "w", (8, 0)),
                ("FORMATO", "w", (8, 0)),
                ("TAMANHO", "e", (8, 0)),
                ("AÇÃO", "e", (8, 0)),
            )
        ):
            width = 44 if col == 0 else (56 if col >= 4 else 0)
            lbl = ctk.CTkLabel(
                cols,
                text=text,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=TEXT_MUTED,
                anchor=sticky,
                width=width if width else 0,
            )
            lbl.grid(row=0, column=col, sticky=sticky, padx=padx)

        ctk.CTkFrame(self._table_card, height=1, fg_color=CARD_BORDER).grid(
            row=0, column=0, sticky="ew", padx=16, pady=(36, 0)
        )

        self._rows_scroll = ctk.CTkScrollableFrame(
            self._table_card,
            fg_color="transparent",
            height=360,
        )
        self._rows_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 12))
        self._rows_scroll.grid_columnconfigure(1, weight=1)

    def set_entries(self, entries: list[DownloadHistoryEntry]) -> None:
        self._entries = list(entries)
        self._render_rows()

    def _filtered_entries(self) -> list[DownloadHistoryEntry]:
        query = self._filter_var.get().strip().casefold()
        if not query:
            return self._entries
        return [e for e in self._entries if query in e.title.casefold()]

    def _render_rows(self) -> None:
        for child in self._rows_scroll.winfo_children():
            child.destroy()

        visible = self._filtered_entries()
        if not visible:
            if not self._entries:
                msg = "Nenhum download no histórico."
            else:
                msg = "Nenhum resultado para este filtro."
            ctk.CTkLabel(
                self._rows_scroll,
                text=msg,
                font=ctk.CTkFont(size=13),
                text_color=TEXT_MUTED,
            ).grid(row=0, column=0, columnspan=6, pady=32, padx=16)
            return

        for row_idx, entry in enumerate(visible):
            self._add_row(row_idx, entry)

    def _add_row(self, row_idx: int, entry: DownloadHistoryEntry) -> None:
        row = ctk.CTkFrame(self._rows_scroll, fg_color="transparent")
        row.grid(row=row_idx, column=0, sticky="ew", pady=2)
        row.grid_columnconfigure(1, weight=1)

        icon_char = "♪" if entry.is_audio else "▶"
        icon_box = ctk.CTkFrame(
            row,
            width=36,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            corner_radius=6,
        )
        icon_box.grid(row=0, column=0, padx=(8, 12))
        icon_box.grid_propagate(False)
        ctk.CTkLabel(
            icon_box,
            text=icon_char,
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECONDARY,
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            row,
            text=entry.title,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(
            row,
            text=format_relative_date(entry.completed_at),
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            width=110,
            anchor="w",
        ).grid(row=0, column=2, padx=(0, 8))

        fmt_box = ctk.CTkFrame(
            row,
            width=52,
            height=26,
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            corner_radius=4,
        )
        fmt_box.grid(row=0, column=3, padx=(0, 8))
        fmt_box.grid_propagate(False)
        ctk.CTkLabel(
            fmt_box,
            text=entry.format_ext,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            row,
            text=format_file_size(entry.size_bytes),
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            width=72,
            anchor="e",
        ).grid(row=0, column=4, padx=(0, 8))

        path = entry.filepath
        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.grid(row=0, column=5, padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="📁",
            width=32,
            height=32,
            command=lambda p=path: self._on_open_folder(p),
            **SECONDARY_BTN,
        ).pack(side="left", padx=(0, 4))
        file_state = "normal" if os.path.isfile(path) else "disabled"
        ctk.CTkButton(
            actions,
            text="📄",
            width=32,
            height=32,
            state=file_state,
            command=lambda p=path: self._on_open_file(p),
            **SECONDARY_BTN,
        ).pack(side="left", padx=(0, 4))
        redo_state = "normal" if entry.source_url.strip() else "disabled"
        ctk.CTkButton(
            actions,
            text="↻",
            width=32,
            height=32,
            state=redo_state,
            command=lambda u=entry.source_url, t=entry.title: self._on_redownload(u, t),
            **SECONDARY_BTN,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            actions,
            text="🗑",
            width=32,
            height=32,
            command=lambda p=path: self._remove_entry(p),
            **SECONDARY_BTN,
        ).pack(side="left")

    def _remove_entry(self, filepath: str) -> None:
        self.set_entries(self._on_remove(filepath))
