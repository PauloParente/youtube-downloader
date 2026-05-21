"""Startup import graph: heavy deps must not load before MainWindow is needed."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture
def clean_heavy_modules():
    for name in list(sys.modules):
        if name == "yt_dlp" or name.startswith("yt_dlp."):
            del sys.modules[name]
        if name == "PIL" or name.startswith("PIL."):
            del sys.modules[name]
    yield
    for name in list(sys.modules):
        if name.startswith("youtube_downloader."):
            del sys.modules[name]


def test_startup_module_does_not_import_ytdlp(clean_heavy_modules):
    import youtube_downloader.ui_qt.startup  # noqa: F401

    assert "yt_dlp" not in sys.modules


def test_app_entry_does_not_import_main_window(clean_heavy_modules):
    import youtube_downloader.app  # noqa: F401

    assert "youtube_downloader.ui_qt.main_window" not in sys.modules
    assert "yt_dlp" not in sys.modules
