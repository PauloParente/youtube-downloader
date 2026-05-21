"""Tests for core.path_utils."""

import sys
from unittest.mock import MagicMock

import pytest

from youtube_downloader.core.path_utils import open_path_in_explorer


def test_open_path_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    startfile = MagicMock()
    monkeypatch.setattr("youtube_downloader.core.path_utils.os.startfile", startfile)
    open_path_in_explorer(r"C:\downloads\video.mp4")
    startfile.assert_called_once_with(r"C:\downloads\video.mp4")


def test_open_path_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    run = MagicMock()
    monkeypatch.setattr("youtube_downloader.core.path_utils.subprocess.run", run)
    open_path_in_explorer("/Users/me/Downloads")
    run.assert_called_once_with(["open", "/Users/me/Downloads"], check=False)


def test_open_path_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    run = MagicMock()
    monkeypatch.setattr("youtube_downloader.core.path_utils.subprocess.run", run)
    open_path_in_explorer("/home/me/Downloads")
    run.assert_called_once_with(["xdg-open", "/home/me/Downloads"], check=False)
