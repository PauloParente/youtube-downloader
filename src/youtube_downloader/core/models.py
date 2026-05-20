"""Data models for download jobs and progress events."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from youtube_downloader.core.metadata import VideoPreview


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
    video_format: str = "mp4"
    export_profile: str = "compatible"
    audio_bitrate: str = "192"
    bandwidth_limit_kbps: int = 0
    auto_download_subtitles: bool = False
    notify_on_complete: bool = True
    ui_language: str = "pt-BR"
    cookies_file: str = ""


@dataclass
class ProgressEvent:
    event_type: EventType
    message: str = ""
    percent: Optional[float] = None
    title: Optional[str] = None
    preview: Optional[VideoPreview] = None
    preview_url: Optional[str] = None
    preview_request_id: Optional[int] = None
    playlist_completed: Optional[int] = None
    playlist_total: Optional[int] = None
    filepath: Optional[str] = None
