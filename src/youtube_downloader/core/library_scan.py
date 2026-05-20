"""Scan download folder for media files (Biblioteca)."""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from youtube_downloader.core.download_history import format_file_size

_MEDIA_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mkv",
    ".mp3",
    ".m4a",
    ".opus",
    ".ogg",
    ".wav",
    ".srt",
    ".vtt",
}


@dataclass
class LibraryFile:
    name: str
    filepath: str
    size_bytes: int
    modified_at: str
    is_audio: bool

    @property
    def format_ext(self) -> str:
        return Path(self.filepath).suffix.lstrip(".").upper() or "—"

    @property
    def size_label(self) -> str:
        return format_file_size(self.size_bytes)


def scan_library_folder(folder: str, *, limit: int = 200) -> list[LibraryFile]:
    """List media files in folder, newest first."""
    root = Path(folder)
    if not root.is_dir():
        return []

    items: list[LibraryFile] = []
    for path in root.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in _MEDIA_EXTENSIONS:
            continue
        if _is_partial_fragment(path.name):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        ext = path.suffix.lstrip(".").lower()
        items.append(
            LibraryFile(
                name=path.stem,
                filepath=str(path.resolve()),
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(
                    timespec="seconds"
                ),
                is_audio=ext in ("mp3", "m4a", "opus", "ogg", "wav"),
            )
        )

    items.sort(key=lambda f: f.modified_at, reverse=True)
    return items[:limit]


def _is_partial_fragment(name: str) -> bool:
    import re

    return bool(re.search(r"\.f\d+\.", name, re.IGNORECASE))
