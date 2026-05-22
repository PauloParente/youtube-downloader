"""Layout breakpoint policy."""

from youtube_downloader.ui_qt.layout_breakpoints import (
    content_width,
    downloads_toolbar_compact,
    queue_layout_mode,
)
from youtube_downloader.ui_qt.theme_tokens import CONTENT_BREAKPOINT_COMPACT, SIDEBAR_WIDTH


def test_content_width_subtracts_sidebar() -> None:
    assert content_width(980) == 980 - SIDEBAR_WIDTH
    assert content_width(900) == 680


def test_content_width_never_negative() -> None:
    assert content_width(100) == 0


def test_queue_layout_mode_columns_at_breakpoint() -> None:
    assert queue_layout_mode(CONTENT_BREAKPOINT_COMPACT) == "columns"
    assert queue_layout_mode(CONTENT_BREAKPOINT_COMPACT + 1) == "columns"


def test_queue_layout_mode_stacked_below_breakpoint() -> None:
    assert queue_layout_mode(CONTENT_BREAKPOINT_COMPACT - 1) == "stacked"
    assert queue_layout_mode(0) == "stacked"


def test_queue_at_window_minimum_is_stacked() -> None:
    # WINDOW_MIN_WIDTH 900 → content ~680 < 720
    assert queue_layout_mode(content_width(900)) == "stacked"


def test_downloads_toolbar_compact_below_breakpoint() -> None:
    assert downloads_toolbar_compact(CONTENT_BREAKPOINT_COMPACT - 1) is True
    assert downloads_toolbar_compact(CONTENT_BREAKPOINT_COMPACT) is False
