"""Dialog when a watch URL includes a playlist (list= parameter)."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from youtube_downloader.core.playlist_urls import PlaylistMode
from youtube_downloader.ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    APP_BG,
    CARD_STYLE,
    PRIMARY_BTN,
    SECONDARY_BTN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

PlaylistChoice = Optional[PlaylistMode]


def ask_video_in_playlist_choice(
    parent: ctk.CTk,
    *,
    playlist_count: int | None = None,
) -> PlaylistChoice:
    """
    Ask whether to download only the current video or the full playlist.

    Returns "single", "full", or None if cancelled.
    """
    result: dict[str, PlaylistChoice] = {"value": None}

    dialog = ctk.CTkToplevel(parent)
    dialog.title("Playlist detectada")
    dialog.configure(fg_color=APP_BG)
    dialog.transient(parent)
    dialog.grab_set()

    frame = ctk.CTkFrame(dialog, **CARD_STYLE)
    frame.pack(padx=20, pady=20, fill="both", expand=True)

    count_hint = ""
    if playlist_count is not None and playlist_count > 0:
        count_hint = f" ({playlist_count} vídeos)"

    ctk.CTkLabel(
        frame,
        text="Esta URL abre um vídeo dentro de uma playlist.",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=TEXT_PRIMARY,
        wraplength=360,
        justify="left",
    ).pack(anchor="w", padx=16, pady=(16, 8))

    ctk.CTkLabel(
        frame,
        text="O que deseja baixar?",
        font=ctk.CTkFont(size=12),
        text_color=TEXT_SECONDARY,
        wraplength=360,
        justify="left",
    ).pack(anchor="w", padx=16, pady=(0, 16))

    def choose(mode: PlaylistMode) -> None:
        result["value"] = mode
        dialog.grab_release()
        dialog.destroy()

    def cancel() -> None:
        result["value"] = None
        dialog.grab_release()
        dialog.destroy()

    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.pack(fill="x", padx=16, pady=(0, 16))

    ctk.CTkButton(
        btn_frame,
        text="Só este vídeo",
        command=lambda: choose("single"),
        **PRIMARY_BTN,
    ).pack(fill="x", pady=4)

    ctk.CTkButton(
        btn_frame,
        text=f"Playlist inteira{count_hint}",
        command=lambda: choose("full"),
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color=TEXT_PRIMARY,
        height=PRIMARY_BTN.get("height", 40),
        corner_radius=PRIMARY_BTN.get("corner_radius", 8),
        font=PRIMARY_BTN.get("font"),
    ).pack(fill="x", pady=4)

    ctk.CTkButton(
        btn_frame,
        text="Cancelar",
        command=cancel,
        **SECONDARY_BTN,
    ).pack(fill="x", pady=(8, 0))

    dialog.update_idletasks()
    w = max(dialog.winfo_reqwidth(), 400)
    h = dialog.winfo_reqheight()
    px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    dialog.geometry(f"{w}x{h}+{px}+{py}")

    dialog.protocol("WM_DELETE_WINDOW", cancel)
    parent.wait_window(dialog)
    return result["value"]
