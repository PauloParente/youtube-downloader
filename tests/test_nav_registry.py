"""Navigation registry — single source for sidebar items and stack indices."""

from youtube_downloader.ui_qt.nav_registry import (
    DEFAULT_VIEW_ID,
    NAV_ITEMS,
    nav_item,
    stack_index,
    view_ids,
)
from youtube_downloader.ui_qt.nav_shortcuts import NAV_VIEW_SHORTCUTS
from youtube_downloader.ui_qt.nav_sidebar import NavSidebar


def test_nav_items_count() -> None:
    assert len(NAV_ITEMS) == 5


def test_stack_index_matches_item_position() -> None:
    for index, item in enumerate(NAV_ITEMS):
        assert stack_index(item.view_id) == index


def test_stack_index_unknown_returns_none() -> None:
    assert stack_index("unknown") is None


def test_view_ids_order() -> None:
    assert view_ids() == tuple(item.view_id for item in NAV_ITEMS)


def test_all_main_items_have_shortcuts() -> None:
    assert len(NAV_VIEW_SHORTCUTS) == len(NAV_ITEMS)
    for item in NAV_ITEMS:
        assert item.shortcut is not None


def test_nav_shortcuts_match_registry() -> None:
    registry_pairs = tuple((item.view_id, item.shortcut) for item in NAV_ITEMS)
    assert NAV_VIEW_SHORTCUTS == registry_pairs


def test_sidebar_items_alias_registry() -> None:
    assert NavSidebar.ITEMS == tuple(
        (item.view_id, item.icon, item.label) for item in NAV_ITEMS
    )


def test_default_view_is_downloads() -> None:
    assert DEFAULT_VIEW_ID == "download"
    assert nav_item(DEFAULT_VIEW_ID) is not None
