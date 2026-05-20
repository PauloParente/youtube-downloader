"""Modal About dialog."""

from __future__ import annotations

import sys
import webbrowser
from collections.abc import Callable
from typing import Optional

import customtkinter as ctk
import yt_dlp

from youtube_downloader.config import (
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    COPYRIGHT_LINE,
    GITHUB_REPO_URL,
    PROJECT_ROOT,
)
from youtube_downloader.core.ffmpeg_utils import find_ffmpeg_dir, is_bundled_ffmpeg
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui.theme import (
    ACCENT,
    APP_BG,
    BTN_SECONDARY,
    CARD_STYLE,
    FONT_BODY,
    GHOST_BTN,
    PRIMARY_BTN,
    SECONDARY_BTN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def _build_about_text() -> str:
    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    ctk_version = getattr(ctk, "__version__", "?")
    if is_bundled_ffmpeg():
        ffmpeg_line = "FFmpeg: embutido (build .exe) ou pasta do app"
    else:
        ffmpeg_dir = find_ffmpeg_dir() or "não encontrado"
        ffmpeg_line = f"FFmpeg: {truncate_text(str(ffmpeg_dir), 56)}"
    run_mode = (
        "Aplicativo empacotado (.exe)"
        if getattr(sys, "frozen", False)
        else "Python (desenvolvimento)"
    )
    data_dir = truncate_text(str(PROJECT_ROOT.resolve()), 56)

    return "\n".join(
        [
            f"{APP_TITLE}  v{APP_VERSION}",
            APP_DESCRIPTION,
            COPYRIGHT_LINE,
            "",
            "Ambiente",
            f"  Python {python_version}",
            f"  CustomTkinter {ctk_version}",
            f"  yt-dlp {yt_dlp.version.__version__}",
            f"  {ffmpeg_line}",
            f"  Modo: {run_mode}",
            "",
            "Dados locais",
            f"  Pasta do app: {data_dir}",
            "  settings.json, history.json, downloads/ e logs/ nesta pasta.",
            "",
            "Atalhos de teclado",
            "  Ctrl+V — colar URL na tela Downloads",
            "  Ctrl+, — abrir Configurações",
        ]
    )


def show_about_dialog(
    master: ctk.CTk,
    *,
    on_open_logs: Callable[[], None],
    existing: Optional[ctk.CTkToplevel] = None,
) -> ctk.CTkToplevel:
    """Open or replace the About modal. Always rebuilds content (avoids empty reuse)."""
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.destroy()
        except Exception:
            pass

    dialog = ctk.CTkToplevel(master)
    dialog.title("Sobre")
    dialog.geometry("480x500")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.configure(fg_color=APP_BG)

    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(2, weight=1)

    ctk.CTkFrame(dialog, height=3, fg_color=ACCENT, corner_radius=0).grid(
        row=0, column=0, sticky="ew"
    )

    header = ctk.CTkFrame(dialog, fg_color=APP_BG)
    header.grid(row=1, column=0, sticky="ew", padx=20, pady=(14, 8))
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        header,
        text="Sobre",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=TEXT_PRIMARY,
        anchor="w",
    ).grid(row=0, column=0, sticky="w")
    ctk.CTkButton(
        header,
        text="✕",
        command=dialog.destroy,
        **GHOST_BTN,
    ).grid(row=0, column=1)

    text_box = ctk.CTkTextbox(
        dialog,
        height=300,
        wrap="word",
        fg_color=("#161616", "#161616"),
        border_color=CARD_STYLE["border_color"],
        border_width=1,
        text_color=TEXT_SECONDARY,
        font=ctk.CTkFont(family=FONT_BODY[0], size=12),
    )
    text_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 8))
    text_box.insert("1.0", _build_about_text())
    text_box.configure(state="disabled")

    btn_row = ctk.CTkFrame(dialog, fg_color=APP_BG)
    btn_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 18))
    ctk.CTkButton(
        btn_row,
        text="Ver logs",
        width=110,
        command=on_open_logs,
        **SECONDARY_BTN,
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        btn_row,
        text="GitHub",
        width=100,
        command=lambda: webbrowser.open(GITHUB_REPO_URL),
        **SECONDARY_BTN,
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        btn_row,
        text="OK",
        width=100,
        command=dialog.destroy,
        **PRIMARY_BTN,
    ).pack(side="right")

    dialog.update_idletasks()
    dialog.grab_set()
    dialog.focus_force()
    return dialog
