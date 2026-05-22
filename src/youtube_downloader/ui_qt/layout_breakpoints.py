"""Layout breakpoints — pure policy (no Qt dependency)."""

from __future__ import annotations

from typing import Literal

from youtube_downloader.ui_qt.theme_tokens import CONTENT_BREAKPOINT_COMPACT, SIDEBAR_WIDTH

QueueLayoutMode = Literal["columns", "stacked"]


def content_width(window_width: int, *, sidebar_width: int = SIDEBAR_WIDTH) -> int:
    """Usable horizontal space for the main content stack (window minus sidebar)."""
    return max(0, window_width - sidebar_width)


def queue_layout_mode(content_width_px: int) -> QueueLayoutMode:
    """Fila: duas colunas (confortável) ou empilhado (compacto)."""
    if content_width_px < CONTENT_BREAKPOINT_COMPACT:
        return "stacked"
    return "columns"


def downloads_toolbar_compact(content_width_px: int) -> bool:
    """Downloads: toolbar e dock em modo compacto (ícones, overflow)."""
    return content_width_px < CONTENT_BREAKPOINT_COMPACT
