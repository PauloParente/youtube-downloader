"""Keyboard shortcuts and badge helpers for sidebar navigation."""

from __future__ import annotations

from youtube_downloader.ui_qt.nav_registry import NAV_ITEMS

NAV_VIEW_SHORTCUTS: tuple[tuple[str, str], ...] = tuple(
    (item.view_id, item.shortcut)
    for item in NAV_ITEMS
    if item.shortcut is not None
)


def shortcut_for_view(view_id: str) -> str | None:
    for vid, seq in NAV_VIEW_SHORTCUTS:
        if vid == view_id:
            return seq
    return None


def nav_tooltip(label: str, view_id: str) -> str:
    seq = shortcut_for_view(view_id)
    if seq is None:
        return label
    return f"{label} ({seq})"


def format_queue_badge(count: int) -> str | None:
    """Badge text for queue count, or None when hidden."""
    if count <= 0:
        return None
    if count > 99:
        return "99+"
    return str(count)
