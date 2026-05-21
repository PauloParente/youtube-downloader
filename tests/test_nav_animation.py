"""Sidebar nav animation helpers."""

from PySide6.QtCore import QRect

from youtube_downloader.ui_qt.nav_anim import (
    lerp_hex_color,
    lerp_int,
    nav_row_highlight_rectf,
    pill_geometry_for_row,
)
from youtube_downloader.ui_qt.theme_tokens import (
    NAV_ANIM_HOVER_IN_MS,
    NAV_ANIM_SELECT_MS,
    NAV_ICON_SYNC_RATIO,
)


def test_lerp_int_midpoint() -> None:
    assert lerp_int(0, 100, 0.5) == 50
    assert lerp_int(0, 100, 0.0) == 0
    assert lerp_int(0, 100, 1.0) == 100


def test_lerp_hex_color() -> None:
    mid = lerp_hex_color("#000000", "#FFFFFF", 0.5)
    assert mid == "#808080"


def test_pill_geometry_for_row() -> None:
    row = QRect(0, 24, 200, 40)
    pill = pill_geometry_for_row(row)
    assert pill.x() == 0
    assert pill.y() == 24
    assert pill.width() == 200
    assert pill.height() == 40


def test_nav_row_highlight_rectf() -> None:
    rect = nav_row_highlight_rectf(200, 40)
    assert rect.x() == 1
    assert rect.y() == 1
    assert rect.width() == 198
    assert rect.height() == 38


def test_pill_geometry_inset() -> None:
    row = QRect(10, 0, 180, 36)
    pill = pill_geometry_for_row(row, inset_x=4)
    assert pill.x() == 4
    assert pill.width() == 172


def test_nav_timing_tokens() -> None:
    assert NAV_ANIM_SELECT_MS == 200
    assert NAV_ANIM_HOVER_IN_MS == 140
    assert 0 < NAV_ICON_SYNC_RATIO < 1
