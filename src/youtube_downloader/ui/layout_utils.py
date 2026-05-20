"""Helpers for responsive Tk / CustomTkinter layout."""

from __future__ import annotations

import customtkinter as ctk


def clamp_wraplength(
    width: int,
    *,
    fraction: float = 0.9,
    min_px: int = 200,
    max_px: int = 640,
) -> int:
    """Map widget width to a safe CTkLabel wraplength."""
    if width <= 1:
        return max_px
    return max(min_px, min(max_px, int(width * fraction)))


def apply_wraplength_from_widget(
    label: ctk.CTkLabel,
    container: ctk.CTkBaseClass,
    *,
    fraction: float = 0.9,
    min_px: int = 200,
    max_px: int = 640,
    pad: int = 24,
) -> None:
    """Set label wraplength from container current width."""
    try:
        width = container.winfo_width()
    except Exception:
        return
    if width <= 1:
        return
    label.configure(wraplength=clamp_wraplength(width - pad, fraction=fraction, min_px=min_px, max_px=max_px))
