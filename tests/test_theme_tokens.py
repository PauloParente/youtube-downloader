"""Design token conventions."""

from youtube_downloader.ui_qt.theme_tokens import (
    CONTENT_BREAKPOINT_COMPACT,
    ICON_LG,
    ICON_MD,
    ICON_SM,
    ICON_XS,
    QUEUE_PENDING_SCROLL_MIN_HEIGHT,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    TITLE_BAR_ICON_SIZE,
)


def test_spacing_on_4px_grid() -> None:
    for value in (SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL):
        assert value % 4 == 0


def test_icon_sizes_use_documented_scale() -> None:
    allowed = {12, 16, 18, 24}
    for value in (ICON_XS, ICON_SM, ICON_MD, ICON_LG):
        assert value in allowed
    assert TITLE_BAR_ICON_SIZE == ICON_XS


def test_content_breakpoint_on_8px_grid() -> None:
    assert CONTENT_BREAKPOINT_COMPACT % 8 == 0


def test_queue_scroll_min_heights() -> None:
    assert QUEUE_PENDING_SCROLL_MIN_HEIGHT % 8 == 0
