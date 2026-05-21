"""Pure helpers for URL resolution outcomes (enqueue vs start download)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

from youtube_downloader.core.playlist_urls import PlaylistMode, UrlKind

DownloadAction = Literal["download", "enqueue"]


def needs_network_expand(kind: UrlKind, playlist_mode: Optional[PlaylistMode]) -> bool:
    """True when playlist expansion requires a network call."""
    if kind == UrlKind.PLAYLIST:
        return True
    if kind == UrlKind.VIDEO_IN_PLAYLIST and playlist_mode == "full":
        return True
    return False


def format_enqueue_log(added: int, total: int) -> str:
    """User-facing log line after enqueueing one or many URLs."""
    if total <= 1:
        if added:
            return "Adicionado à fila."
        return "URL já está na fila."
    skipped = total - added
    msg = f"Playlist: {added} vídeo(s) adicionados à fila."
    if skipped:
        msg += f" ({skipped} já estavam na fila.)"
    return msg


def format_playlist_download_start_log(
    total_videos: int, *, added_rest: int, skipped: int
) -> str:
    """Log when Baixar starts the first video of a multi-item playlist."""
    if total_videos <= 1:
        return "Playlist: 1 vídeo — iniciando."
    msg = (
        f"Playlist: {total_videos} vídeos — iniciando o primeiro"
        f", {added_rest} na fila"
    )
    if skipped:
        msg += f" ({skipped} já estavam na fila)"
    return msg + "."


class ResolvedUrlPlanKind(str, Enum):
    NO_VIDEOS = "no_videos"
    START_SINGLE = "start_single"
    ENQUEUE_ALL = "enqueue_all"
    START_FIRST_ENQUEUE_REST = "start_first_enqueue_rest"


@dataclass(frozen=True)
class ResolvedUrlPlan:
    kind: ResolvedUrlPlanKind
    start_url: str = ""
    enqueue_urls: tuple[str, ...] = ()

    @property
    def urls_to_enqueue(self) -> list[str]:
        return list(self.enqueue_urls)


def plan_resolved_urls(
    urls: list[str],
    action: DownloadAction,
    *,
    is_downloading: bool,
) -> ResolvedUrlPlan:
    """Map resolved watch URLs to the next UI/download action (no I/O)."""
    if not urls:
        return ResolvedUrlPlan(ResolvedUrlPlanKind.NO_VIDEOS)

    if len(urls) == 1:
        if action == "enqueue":
            return ResolvedUrlPlan(
                ResolvedUrlPlanKind.ENQUEUE_ALL,
                enqueue_urls=(urls[0],),
            )
        return ResolvedUrlPlan(
            ResolvedUrlPlanKind.START_SINGLE,
            start_url=urls[0],
        )

    if action == "enqueue":
        return ResolvedUrlPlan(
            ResolvedUrlPlanKind.ENQUEUE_ALL,
            enqueue_urls=tuple(urls),
        )

    if is_downloading:
        return ResolvedUrlPlan(
            ResolvedUrlPlanKind.ENQUEUE_ALL,
            enqueue_urls=tuple(urls),
        )

    return ResolvedUrlPlan(
        ResolvedUrlPlanKind.START_FIRST_ENQUEUE_REST,
        start_url=urls[0],
        enqueue_urls=tuple(urls[1:]),
    )
