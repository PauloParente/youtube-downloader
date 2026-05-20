"""Classify YouTube URLs and expand playlists into per-video watch URLs."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal, Optional
from urllib.parse import parse_qs, urlparse

import yt_dlp

from youtube_downloader.core.logging_config import get_logger

logger = get_logger("playlist_urls")

# YouTube video IDs are 11 characters; playlist IDs (PL…) are longer and must not be used as v=
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
WATCH_VIDEO_RE = re.compile(
    r"(?:youtube\.com/watch|youtu\.be/)(?:.*[?&])?v=([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)
PLAYLIST_PAGE_RE = re.compile(
    r"youtube\.com/playlist\?",
    re.IGNORECASE,
)

PlaylistMode = Literal["single", "full"]


class UrlKind(str, Enum):
    VIDEO = "video"
    PLAYLIST = "playlist"
    VIDEO_IN_PLAYLIST = "video_in_playlist"


class PlaylistExpandError(Exception):
    """Raised when playlist metadata cannot be extracted."""


def classify_youtube_url(url: str) -> UrlKind:
    """Classify a YouTube URL for enqueue/download resolution."""
    text = url.strip()
    if not text:
        return UrlKind.VIDEO

    if PLAYLIST_PAGE_RE.search(text):
        return UrlKind.PLAYLIST

    parsed = urlparse(text)
    query = parse_qs(parsed.query)
    has_list = bool(query.get("list"))
    has_video = bool(_video_id_from_url(text))

    if has_list and has_video:
        return UrlKind.VIDEO_IN_PLAYLIST
    if has_list:
        return UrlKind.PLAYLIST

    return UrlKind.VIDEO


def is_valid_video_id(video_id: str) -> bool:
    return bool(video_id and VIDEO_ID_RE.fullmatch(video_id))


def watch_url_for_video_id(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def list_id_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url.strip())
    query = parse_qs(parsed.query)
    ids = query.get("list")
    if ids and ids[0].strip():
        return ids[0].strip()
    return None


def playlist_page_url(url: str) -> str:
    """
    Canonical playlist URL for yt-dlp expansion.

    watch?v=VIDEO&list=PLAYLIST must use playlist?list=… so all entries are returned.
    """
    cleaned = url.strip()
    list_id = list_id_from_url(cleaned)
    if list_id:
        return f"https://www.youtube.com/playlist?list={list_id}"
    if PLAYLIST_PAGE_RE.search(cleaned):
        return cleaned
    return cleaned


def _video_id_from_url(url: str) -> Optional[str]:
    match = WATCH_VIDEO_RE.search(url)
    if match:
        return match.group(1)
    parsed = urlparse(url.strip())
    query = parse_qs(parsed.query)
    ids = query.get("v")
    if ids and ids[0] and is_valid_video_id(ids[0]):
        return ids[0]
    if "youtu.be" in (parsed.netloc or "").lower():
        path = (parsed.path or "").strip("/")
        if path and is_valid_video_id(path.split("/")[0][:11]):
            return path.split("/")[0][:11]
    return None


def _entries_from_info(info: dict[str, Any]) -> list[dict[str, Any]]:
    entries = info.get("entries")
    if entries is None:
        return []
    if isinstance(entries, list):
        return [e for e in entries if e]
    return []


def _video_urls_from_entries(entries: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        video_id = entry.get("id")
        if not video_id or not is_valid_video_id(str(video_id)):
            continue
        watch = watch_url_for_video_id(str(video_id))
        if watch not in seen:
            seen.add(watch)
            urls.append(watch)
    return urls


def expand_playlist_urls(url: str) -> list[str]:
    """Return watch URLs for each item in a playlist (network via yt-dlp)."""
    cleaned = url.strip()
    if not cleaned:
        raise PlaylistExpandError("URL vazia.")

    extract_url = playlist_page_url(cleaned)
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(extract_url, download=False)
    except Exception as exc:
        logger.exception("Falha ao expandir playlist: %s", extract_url[:80])
        raise PlaylistExpandError(str(exc)) from exc

    if not info:
        raise PlaylistExpandError("Não foi possível obter informações da playlist.")

    urls = _video_urls_from_entries(_entries_from_info(info))

    if not urls:
        raise PlaylistExpandError("Playlist sem vídeos disponíveis.")

    logger.info(
        "Playlist expandida: %s -> %d vídeos (via %s)",
        cleaned[:60],
        len(urls),
        extract_url[:60],
    )
    return urls


def resolve_download_urls(
    url: str,
    *,
    playlist_mode: Optional[PlaylistMode] = None,
) -> list[str]:
    """
    Resolve a pasted URL into one or more per-video watch URLs.

    playlist_mode is required for VIDEO_IN_PLAYLIST:
    - "single": only the video in the URL
    - "full": expand the whole playlist
    """
    cleaned = url.strip()
    kind = classify_youtube_url(cleaned)

    if kind == UrlKind.VIDEO:
        video_id = _video_id_from_url(cleaned)
        if video_id:
            return [watch_url_for_video_id(video_id)]
        return [cleaned]

    if kind == UrlKind.PLAYLIST:
        return expand_playlist_urls(cleaned)

    if kind == UrlKind.VIDEO_IN_PLAYLIST:
        if playlist_mode == "single":
            video_id = _video_id_from_url(cleaned)
            if video_id:
                return [watch_url_for_video_id(video_id)]
            return [cleaned]
        if playlist_mode == "full":
            return expand_playlist_urls(cleaned)
        raise ValueError("playlist_mode required for video_in_playlist URLs")

    return [cleaned]
