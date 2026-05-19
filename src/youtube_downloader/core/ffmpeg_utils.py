"""Locate FFmpeg: bundled with app, then PATH, then LOCALAPPDATA."""

import os
import shutil
from typing import Optional

from youtube_downloader.config import get_project_root

FFMPEG_SUBDIR = "ffmpeg"
FFMPEG_EXE = "ffmpeg.exe"
FFPROBE_EXE = "ffprobe.exe"


def _bundled_ffmpeg_dir() -> Optional[str]:
    bundled = get_project_root() / FFMPEG_SUBDIR
    if (bundled / FFMPEG_EXE).is_file():
        return str(bundled.resolve())
    return None


def _localappdata_ffmpeg_dir() -> Optional[str]:
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if not localappdata:
        return None

    ffmpeg_root = os.path.join(localappdata, "ffmpeg")
    if not os.path.isdir(ffmpeg_root):
        return None

    for root, _dirs, files in os.walk(ffmpeg_root):
        if FFMPEG_EXE in files:
            return root

    return None


def find_ffmpeg_dir() -> Optional[str]:
    """Return directory containing ffmpeg (for yt-dlp ffmpeg_location)."""
    bundled = _bundled_ffmpeg_dir()
    if bundled:
        return bundled

    path = shutil.which("ffmpeg")
    if path:
        return os.path.dirname(os.path.abspath(path))

    return _localappdata_ffmpeg_dir()


def is_bundled_ffmpeg() -> bool:
    return _bundled_ffmpeg_dir() is not None


def ffmpeg_available() -> bool:
    return find_ffmpeg_dir() is not None
