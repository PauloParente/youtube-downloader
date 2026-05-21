"""Bundled SVG icons."""

from youtube_downloader.ui_qt.icons import _icons_dir, _svg_bytes


def test_icons_dir_exists() -> None:
    assert _icons_dir().is_dir()


def test_core_icons_present() -> None:
    for name in (
        "download",
        "queue",
        "settings",
        "folder",
        "play",
        "minimize",
        "maximize",
        "restore",
        "close",
    ):
        assert _svg_bytes(name)
