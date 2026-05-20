"""Biblioteca — arquivos na pasta de downloads."""

from collections.abc import Callable

import customtkinter as ctk

from youtube_downloader.core.library_scan import LibraryFile, scan_library_folder
from youtube_downloader.ui.theme import (
    CARD_STYLE,
    SECONDARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class LibraryView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        get_output_dir: Callable[[], str],
        on_open_path: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._get_output_dir = get_output_dir
        self._on_open_path = on_open_path
        self._files: list[LibraryFile] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        pad = 24
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=pad, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Biblioteca",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Arquivos de mídia na pasta de destino configurada.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        ctk.CTkButton(
            header,
            text="Atualizar",
            width=100,
            command=self.refresh,
            **SECONDARY_BTN,
        ).grid(row=0, column=1, rowspan=2, padx=(12, 0))

        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._status_label.grid(row=1, column=0, sticky="ew", padx=pad, pady=(0, 8))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=pad, pady=(0, 20))
        self._scroll.grid_columnconfigure(0, weight=1)

    def refresh(self) -> None:
        folder = self._get_output_dir().strip()
        self._files = scan_library_folder(folder)
        self._status_label.configure(
            text=f"{len(self._files)} arquivo(s) em {folder}"
            if self._files
            else f"Nenhum arquivo de mídia em {folder}"
        )
        self._render_rows()

    def _render_rows(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()

        if not self._files:
            ctk.CTkLabel(
                self._scroll,
                text="Nenhum arquivo encontrado. Baixe vídeos na tela Downloads.",
                font=ctk.CTkFont(size=13),
                text_color=TEXT_MUTED,
                wraplength=520,
                justify="left",
            ).grid(row=0, column=0, pady=32, padx=8, sticky="w")
            return

        for idx, item in enumerate(self._files):
            row = ctk.CTkFrame(self._scroll, **CARD_STYLE)
            row.grid(row=idx, column=0, sticky="ew", pady=4)
            row.grid_columnconfigure(1, weight=1)

            icon = "♪" if item.is_audio else "▶"
            ctk.CTkLabel(
                row,
                text=icon,
                width=28,
                font=ctk.CTkFont(size=14),
                text_color=TEXT_SECONDARY,
            ).grid(row=0, column=0, padx=(12, 8), pady=10)

            title_col = ctk.CTkFrame(row, fg_color="transparent")
            title_col.grid(row=0, column=1, sticky="ew", pady=8)
            ctk.CTkLabel(
                title_col,
                text=item.name,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                title_col,
                text=f"{item.format_ext} · {item.size_label}",
                font=ctk.CTkFont(size=11),
                text_color=TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w")

            path = item.filepath
            ctk.CTkButton(
                row,
                text="Abrir",
                width=70,
                command=lambda p=path: self._on_open_path(p),
                **SECONDARY_BTN,
            ).grid(row=0, column=2, padx=12, pady=8)
