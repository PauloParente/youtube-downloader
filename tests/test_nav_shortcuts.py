"""Sidebar nav shortcuts and queue badge formatting."""

from youtube_downloader.ui_qt.nav_shortcuts import (
    format_queue_badge,
    nav_tooltip,
    shortcut_for_view,
)


def test_shortcut_for_view() -> None:
    assert shortcut_for_view("queue") == "Ctrl+2"
    assert shortcut_for_view("unknown") is None


def test_nav_tooltip_includes_shortcut() -> None:
    assert "Ctrl+1" in nav_tooltip("Downloads", "download")
    assert nav_tooltip("Sobre", "about") == "Sobre"


def test_format_queue_badge() -> None:
    assert format_queue_badge(0) is None
    assert format_queue_badge(3) == "3"
    assert format_queue_badge(99) == "99"
    assert format_queue_badge(105) == "99+"
