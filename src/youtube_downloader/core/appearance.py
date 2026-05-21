"""Appearance mode helpers (UI settings, no Qt)."""

from __future__ import annotations


def appearance_mode_from_dark_enabled(dark_enabled: bool) -> str:
    return "dark" if dark_enabled else "light"


def dark_enabled_for_mode(mode: str) -> bool:
    return mode == "dark"


def normalize_appearance_mode(mode: str, default: str = "dark") -> str:
    if mode in ("dark", "light"):
        return mode
    return default
