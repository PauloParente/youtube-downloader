"""Persist and format download history entries."""

import hashlib
import io
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from youtube_downloader.config import PROJECT_ROOT
from youtube_downloader.core.logging_config import LOG_CACHE_DIR, get_logger

logger = get_logger("history")

HISTORY_FILE = PROJECT_ROOT / "history.json"
HISTORY_THUMB_DIR = LOG_CACHE_DIR / "history"
_MAX_ENTRIES = 100

_MONTHS_PT = (
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)


@dataclass
class DownloadHistoryEntry:
    title: str
    filepath: str
    completed_at: str
    format_ext: str
    size_bytes: int
    is_audio: bool
    source_url: str = ""
    channel_name: str = ""
    channel_url: str = ""
    thumbnail_path: str = ""

    @classmethod
    def from_filepath(
        cls,
        filepath: str,
        title: str,
        source_url: str = "",
        *,
        channel_name: str = "",
        channel_url: str = "",
        thumbnail_path: str = "",
    ) -> "DownloadHistoryEntry":
        ext = os.path.splitext(filepath)[1].lstrip(".").upper() or "—"
        is_audio = ext in ("MP3", "M4A", "AAC", "OPUS", "OGG", "WAV")
        try:
            size_bytes = os.path.getsize(filepath)
        except OSError:
            size_bytes = 0
        return cls(
            title=title,
            filepath=filepath,
            completed_at=datetime.now().isoformat(timespec="seconds"),
            format_ext=ext,
            size_bytes=size_bytes,
            is_audio=is_audio,
            source_url=source_url.strip(),
            channel_name=channel_name.strip(),
            channel_url=channel_url.strip(),
            thumbnail_path=thumbnail_path.strip(),
        )


def history_thumbnail_path_for_url(source_url: str) -> Path:
    """Stable cache path for a video URL thumbnail."""
    key = hashlib.sha256(source_url.strip().encode("utf-8")).hexdigest()[:16]
    return HISTORY_THUMB_DIR / f"{key}.jpg"


def save_history_thumbnail(source_url: str, thumbnail_bytes: bytes) -> str:
    """Write thumbnail JPEG to cache; returns path string or empty on failure."""
    cleaned = source_url.strip()
    if not cleaned or not thumbnail_bytes:
        return ""
    try:
        from PIL import Image

        HISTORY_THUMB_DIR.mkdir(parents=True, exist_ok=True)
        path = history_thumbnail_path_for_url(cleaned)
        img = Image.open(io.BytesIO(thumbnail_bytes)).convert("RGB")
        img.save(path, "JPEG", quality=85)
        return str(path)
    except Exception:
        logger.exception("Falha ao salvar thumbnail do historico")
        return ""


def delete_history_thumbnail(path: str) -> None:
    cleaned = path.strip()
    if not cleaned:
        return
    try:
        Path(cleaned).unlink(missing_ok=True)
    except OSError:
        logger.warning("Falha ao remover thumbnail do historico: %s", cleaned)


def clear_history_thumbnails() -> None:
    if not HISTORY_THUMB_DIR.is_dir():
        return
    for path in HISTORY_THUMB_DIR.glob("*.jpg"):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 0:
        size_bytes = 0
    if size_bytes < 1024:
        return f"{size_bytes} B"
    size = float(size_bytes)
    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024.0
        if size < 1024.0 or unit == "TB":
            if unit in ("MB", "GB", "TB") and size >= 10:
                return f"{size:.0f} {unit}"
            if unit in ("MB", "GB", "TB"):
                return f"{size:.1f} {unit}"
            return f"{size:.0f} {unit}"
    return f"{size_bytes} B"


def format_relative_date(iso_timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return iso_timestamp

    now = datetime.now()
    if dt.date() == now.date():
        return f"Hoje, {dt.strftime('%H:%M')}"
    yesterday = (now - timedelta(days=1)).date()
    if dt.date() == yesterday:
        return f"Ontem, {dt.strftime('%H:%M')}"
    month = _MONTHS_PT[dt.month - 1]
    return f"{dt.day} {month}, {dt.strftime('%H:%M')}"


def _coerce_entry(data: dict[str, Any]) -> DownloadHistoryEntry | None:
    try:
        return DownloadHistoryEntry(
            title=str(data.get("title", "")),
            filepath=str(data.get("filepath", "")),
            completed_at=str(data.get("completed_at", "")),
            format_ext=str(data.get("format_ext", "—")).upper(),
            size_bytes=int(data.get("size_bytes", 0)),
            is_audio=bool(data.get("is_audio", False)),
            source_url=str(data.get("source_url", "")),
            channel_name=str(data.get("channel_name", "")),
            channel_url=str(data.get("channel_url", "")),
            thumbnail_path=str(data.get("thumbnail_path", "")),
        )
    except (TypeError, ValueError):
        return None


def load_history() -> list[DownloadHistoryEntry]:
    if not HISTORY_FILE.is_file():
        return []
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        entries: list[DownloadHistoryEntry] = []
        for item in raw:
            if isinstance(item, dict):
                entry = _coerce_entry(item)
                if entry and entry.filepath:
                    entries.append(entry)
        return entries
    except Exception:
        logger.exception("Falha ao carregar history.json")
        return []


def save_history(entries: list[DownloadHistoryEntry]) -> None:
    try:
        payload = [asdict(e) for e in entries[:_MAX_ENTRIES]]
        HISTORY_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Falha ao salvar history.json")


def add_history_entry(entry: DownloadHistoryEntry) -> list[DownloadHistoryEntry]:
    entries = load_history()
    entries = [e for e in entries if e.filepath != entry.filepath]
    entries.insert(0, entry)
    entries = entries[:_MAX_ENTRIES]
    save_history(entries)
    return entries


def remove_history_entry(filepath: str) -> list[DownloadHistoryEntry]:
    """Remove one entry by filepath and persist. Returns the updated list."""
    cleaned = filepath.strip()
    if not cleaned:
        return load_history()
    entries = load_history()
    removed = [e for e in entries if e.filepath == cleaned]
    for entry in removed:
        delete_history_thumbnail(entry.thumbnail_path)
    entries = [e for e in entries if e.filepath != cleaned]
    save_history(entries)
    return entries


def clear_history() -> list[DownloadHistoryEntry]:
    """Remove all entries from history.json."""
    clear_history_thumbnails()
    save_history([])
    return []


def refresh_entries_from_disk(
    entries: list[DownloadHistoryEntry],
) -> list[DownloadHistoryEntry]:
    """Re-read file size/format from disk; preserve completed_at and title."""
    refreshed: list[DownloadHistoryEntry] = []
    for entry in entries:
        if os.path.isfile(entry.filepath):
            updated = DownloadHistoryEntry.from_filepath(
                entry.filepath,
                entry.title,
                entry.source_url,
                channel_name=entry.channel_name,
                channel_url=entry.channel_url,
                thumbnail_path=entry.thumbnail_path,
            )
            refreshed.append(
                DownloadHistoryEntry(
                    title=entry.title,
                    filepath=updated.filepath,
                    completed_at=entry.completed_at,
                    format_ext=updated.format_ext,
                    size_bytes=updated.size_bytes,
                    is_audio=updated.is_audio,
                    source_url=entry.source_url,
                    channel_name=entry.channel_name,
                    channel_url=entry.channel_url,
                    thumbnail_path=entry.thumbnail_path,
                )
            )
        else:
            refreshed.append(
                DownloadHistoryEntry(
                    title=entry.title,
                    filepath=entry.filepath,
                    completed_at=entry.completed_at,
                    format_ext=entry.format_ext,
                    size_bytes=0,
                    is_audio=entry.is_audio,
                    source_url=entry.source_url,
                    channel_name=entry.channel_name,
                    channel_url=entry.channel_url,
                    thumbnail_path=entry.thumbnail_path,
                )
            )
    return refreshed


def entry_disk_signature(entry: DownloadHistoryEntry) -> tuple[str, int, str, bool]:
    """Comparable fields that change when a file is moved or updated on disk."""
    return (entry.filepath, entry.size_bytes, entry.format_ext, entry.is_audio)
