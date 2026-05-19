"""Data models for download jobs and progress events."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EventType(str, Enum):
    PROGRESS = "progress"
    LOG = "log"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"
    PREVIEW_LOADING = "preview_loading"
    PREVIEW_READY = "preview_ready"
    PREVIEW_CLEAR = "preview_clear"


@dataclass
class DownloadJob:
    url: str
    output_dir: str
    quality: str
    audio_only: bool
    download_playlist: bool = False


@dataclass
class ProgressEvent:
    event_type: EventType
    message: str = ""
    percent: Optional[float] = None
    title: Optional[str] = None
    preview: Optional[object] = None
    preview_url: Optional[str] = None
    preview_request_id: Optional[int] = None
    playlist_completed: Optional[int] = None
    playlist_total: Optional[int] = None
    filepath: Optional[str] = None
