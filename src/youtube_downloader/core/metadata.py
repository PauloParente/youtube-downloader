"""Fetch video metadata and thumbnail for URL preview."""

import re
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from youtube_downloader.core.download_errors import humanize_ytdlp_error
from youtube_downloader.core.logging_config import get_logger

logger = get_logger("metadata")

YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/",
    re.IGNORECASE,
)


@dataclass
class VideoPreview:
    url: str
    title: str
    thumbnail_bytes: Optional[bytes]
    is_playlist: bool = False
    playlist_count: Optional[int] = None
    playlist_title: Optional[str] = None
    duration_seconds: Optional[int] = None
    uploader: Optional[str] = None
    channel_url: Optional[str] = None
    error: Optional[str] = None


def extract_channel_url(info: dict[str, Any]) -> str:
    """Best-effort channel page URL from yt-dlp extract_info dict."""
    for key in ("channel_url", "uploader_url"):
        value = info.get(key)
        if isinstance(value, str) and value.strip().startswith("http"):
            return value.strip()
    channel_id = info.get("channel_id")
    if channel_id:
        return f"https://www.youtube.com/channel/{channel_id}"
    return ""


def format_duration(seconds: Optional[int]) -> Optional[str]:
    if seconds is None or seconds < 0:
        return None
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def is_youtube_url(url: str) -> bool:
    return bool(url.strip() and YOUTUBE_URL_RE.search(url))


def _pick_thumbnail(info: dict[str, Any]) -> Optional[str]:
    thumb = info.get("thumbnail")
    if thumb:
        return thumb
    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        return thumbnails[-1].get("url")
    return None


def _download_thumbnail(url: str) -> Optional[bytes]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            logger.debug("Thumbnail HTTP ok: %s bytes from %s", len(data), url[:80])
            return data
    except Exception:
        logger.exception("Falha ao baixar thumbnail: %s", url[:80])
        return None


def _entry_has_details(entry: dict[str, Any]) -> bool:
    return bool(entry.get("title") and _pick_thumbnail(entry))


def _resolve_first_entry(
    ydl: Any, info: dict[str, Any]
) -> tuple[dict[str, Any], bool, Optional[int], Optional[str]]:
    entries = info.get("entries")
    if not entries:
        return info, False, None, None

    valid = [e for e in entries if e]
    if not valid:
        return info, True, 0, info.get("title")

    playlist_count = info.get("playlist_count") or info.get("n_entries") or len(valid)
    playlist_title = info.get("title")
    first = valid[0]

    if _entry_has_details(first):
        return first, True, playlist_count, playlist_title

    video_id = first.get("id")
    if video_id:
        try:
            full = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=False,
            )
            if full:
                return full, True, playlist_count, playlist_title
        except Exception:
            logger.exception("Falha ao extrair 1º vídeo da playlist (id=%s)", video_id)

    return first, True, playlist_count, playlist_title


def fetch_preview(url: str) -> VideoPreview:
    """Extract title and thumbnail without downloading media."""
    logger.debug("fetch_preview iniciado: %s", url)
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
    }

    try:
        import yt_dlp

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                logger.warning("extract_info retornou vazio: %s", url)
                return VideoPreview(
                    url=url,
                    title="",
                    thumbnail_bytes=None,
                    error="Não foi possível obter informações do vídeo.",
                )

            video_info, is_playlist, playlist_count, playlist_title = _resolve_first_entry(
                ydl, info
            )
            title = video_info.get("title") or "Sem título"
            thumb_url = _pick_thumbnail(video_info)
            thumb_bytes = _download_thumbnail(thumb_url) if thumb_url else None

            if not thumb_url:
                logger.warning("Sem URL de thumbnail para: %s", url)
            elif not thumb_bytes:
                logger.warning("Thumbnail vazia após download: %s", thumb_url[:80])

            logger.info(
                "fetch_preview ok: title=%r playlist=%s count=%s thumb_bytes=%s",
                title[:60],
                is_playlist,
                playlist_count,
                len(thumb_bytes) if thumb_bytes else 0,
            )

            duration = video_info.get("duration")
            if duration is not None:
                try:
                    duration = int(duration)
                except (TypeError, ValueError):
                    duration = None

            return VideoPreview(
                url=url,
                title=title,
                thumbnail_bytes=thumb_bytes,
                is_playlist=is_playlist,
                playlist_count=playlist_count,
                playlist_title=playlist_title,
                duration_seconds=duration,
                uploader=video_info.get("uploader") or video_info.get("channel"),
                channel_url=extract_channel_url(video_info) or None,
            )
    except Exception as exc:
        logger.exception("fetch_preview falhou: %s", url)
        return VideoPreview(
            url=url,
            title="",
            thumbnail_bytes=None,
            error=humanize_ytdlp_error(str(exc)),
        )
