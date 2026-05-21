"""Appearance mode helpers."""

from youtube_downloader.core.appearance import (
    appearance_mode_from_dark_enabled,
    dark_enabled_for_mode,
    normalize_appearance_mode,
)


def test_appearance_mode_from_dark_enabled() -> None:
    assert appearance_mode_from_dark_enabled(True) == "dark"
    assert appearance_mode_from_dark_enabled(False) == "light"


def test_dark_enabled_for_mode() -> None:
    assert dark_enabled_for_mode("dark") is True
    assert dark_enabled_for_mode("light") is False


def test_normalize_appearance_mode() -> None:
    assert normalize_appearance_mode("dark") == "dark"
    assert normalize_appearance_mode("light") == "light"
    assert normalize_appearance_mode("invalid") == "dark"
    assert normalize_appearance_mode("", default="light") == "light"
