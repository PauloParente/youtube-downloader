"""Left navigation sidebar for the main shell."""

from collections.abc import Callable

import customtkinter as ctk

from youtube_downloader.config import APP_TITLE, APP_VERSION
from youtube_downloader.ui.theme import (
    ACCENT,
    CARD_BORDER,
    NAV_BTN,
    SIDEBAR_ACTIVE_BG,
    SIDEBAR_BG,
    SIDEBAR_WIDTH,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class NavSidebar(ctk.CTkFrame):
    """Sidebar com marca, navegação e ação Sobre no rodapé."""

    ITEMS = (
        ("download", "⬇", "Downloads"),
        ("library", "▦", "Biblioteca"),
        ("history", "↺", "Histórico"),
        ("settings", "⚙", "Configurações"),
    )

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_select: Callable[[str], None],
        on_about: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=SIDEBAR_WIDTH,
            fg_color=SIDEBAR_BG,
            corner_radius=0,
            **kwargs,
        )
        self.grid_propagate(False)
        self._on_select = on_select
        self._on_about = on_about
        self._active_id = "download"
        self._item_frames: dict[str, ctk.CTkFrame] = {}
        self._item_buttons: dict[str, ctk.CTkButton] = {}

        self.grid_rowconfigure(1, weight=1)

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=14, pady=(18, 12))
        brand.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            brand,
            text="▶",
            width=36,
            height=36,
            fg_color=ACCENT,
            corner_radius=8,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, rowspan=2, padx=(0, 10))

        ctk.CTkLabel(
            brand,
            text=APP_TITLE,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            brand,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=1, sticky="w")

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        for view_id, icon, label in self.ITEMS:
            row = ctk.CTkFrame(nav, fg_color="transparent", corner_radius=8)
            row.pack(fill="x", pady=2)
            self._item_frames[view_id] = row

            btn = ctk.CTkButton(
                row,
                text=f"{icon}   {label}",
                command=lambda vid=view_id: self._select(vid),
                font=ctk.CTkFont(size=13),
                **NAV_BTN,
            )
            btn.pack(fill="x", padx=4, pady=5)
            self._item_buttons[view_id] = btn

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 16))

        ctk.CTkFrame(footer, height=1, fg_color=CARD_BORDER).pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            footer,
            text="ℹ   Sobre",
            command=self._on_about,
            font=ctk.CTkFont(size=13),
            **NAV_BTN,
        ).pack(fill="x", pady=4)

        self.set_active("download")

    def _select(self, view_id: str) -> None:
        self.set_active(view_id)
        self._on_select(view_id)

    def set_active(self, view_id: str) -> None:
        self._active_id = view_id
        for vid, row in self._item_frames.items():
            btn = self._item_buttons[vid]
            if vid == view_id:
                row.configure(fg_color=SIDEBAR_ACTIVE_BG)
                btn.configure(text_color=ACCENT)
            else:
                row.configure(fg_color="transparent")
                btn.configure(text_color=TEXT_SECONDARY)
