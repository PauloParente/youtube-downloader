"""Splash screen shown while the main UI loads."""

from __future__ import annotations

from typing import Optional, Union

import customtkinter as ctk

from youtube_downloader.config import (
    APP_TITLE,
    APP_VERSION,
    SPLASH_LOGO_PATH,
    SPLASH_SIZE,
)
from youtube_downloader.ui.theme import (
    ACCENT,
    APP_BG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

SPLASH_STATUS_TEXT = "A carregar. Por favor, aguarde…"

TkWindow = Union[ctk.CTk, ctk.CTkToplevel]


def center_window_on_screen(window: TkWindow, width: int, height: int) -> None:
    """Place *window* at the center of the primary screen."""
    window.update_idletasks()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def parse_window_size(size: str) -> tuple[int, int]:
    """Parse ``WxH`` geometry strings (e.g. ``980x720``)."""
    parts = size.lower().split("x", 1)
    return int(parts[0]), int(parts[1])


class SplashScreen:
    """Splash in a separate borderless window; main app stays hidden until startup ends."""

    def __init__(self, app: ctk.CTk) -> None:
        self._app = app
        self._width, self._height = parse_window_size(SPLASH_SIZE)
        self._logo_image: Optional[ctk.CTkImage] = None
        self._top: Optional[ctk.CTkToplevel] = None

    def show_window(self) -> None:
        """Show splash toplevel centered on screen."""
        self._top = ctk.CTkToplevel(self._app)
        self._top.overrideredirect(True)
        self._top.configure(fg_color=APP_BG)
        self._top.attributes("-topmost", True)
        center_window_on_screen(self._top, self._width, self._height)

        root = self._top
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)

        content = ctk.CTkFrame(root, fg_color=APP_BG, corner_radius=0)
        content.grid(row=1, column=0, sticky="nsew", padx=40, pady=24)
        content.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(content, fg_color="transparent")
        brand.grid(row=0, column=0, pady=(0, 20))
        brand.grid_columnconfigure(1, weight=1)

        logo_image = self._load_logo_image()
        if logo_image is not None:
            ctk.CTkLabel(brand, text="", image=logo_image).grid(
                row=0, column=0, rowspan=2, padx=(0, 14)
            )
        else:
            ctk.CTkLabel(
                brand,
                text="▶",
                width=48,
                height=48,
                fg_color=ACCENT,
                corner_radius=10,
                text_color=TEXT_PRIMARY,
                font=ctk.CTkFont(size=20, weight="bold"),
            ).grid(row=0, column=0, rowspan=2, padx=(0, 14))

        ctk.CTkLabel(
            brand,
            text=APP_TITLE,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            brand,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=1, sticky="w")

        ctk.CTkLabel(
            content,
            text=SPLASH_STATUS_TEXT,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0)

    def _load_logo_image(self) -> Optional[ctk.CTkImage]:
        if not SPLASH_LOGO_PATH.is_file():
            return None
        try:
            from PIL import Image

            img = Image.open(SPLASH_LOGO_PATH)
            self._logo_image = ctk.CTkImage(
                light_image=img, dark_image=img, size=(48, 48)
            )
            return self._logo_image
        except OSError:
            return None

    def destroy(self) -> None:
        if self._top is not None:
            self._top.destroy()
            self._top = None
