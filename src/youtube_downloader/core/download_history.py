"""Persist and format download history entries."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from youtube_downloader.config import PROJECT_ROOT
from youtube_downloader.core.logging_config import get_logger

logger = get_logger("history")

HISTORY_FILE = PROJECT_ROOT / "history.json"
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

    @classmethod
    def from_filepath(cls, filepath: str, title: str) -> "DownloadHistoryEntry":
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
        )


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
