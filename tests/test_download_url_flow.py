"""Tests for core.download_url_flow."""

from youtube_downloader.core.download_url_flow import (
    ResolvedUrlPlanKind,
    format_enqueue_log,
    format_playlist_download_start_log,
    needs_network_expand,
    plan_resolved_urls,
)
from youtube_downloader.core.playlist_urls import UrlKind


def test_needs_network_expand_playlist() -> None:
    assert needs_network_expand(UrlKind.PLAYLIST, None) is True


def test_needs_network_expand_video_in_playlist_full() -> None:
    assert needs_network_expand(UrlKind.VIDEO_IN_PLAYLIST, "full") is True


def test_needs_network_expand_video_single_mode() -> None:
    assert needs_network_expand(UrlKind.VIDEO_IN_PLAYLIST, "single") is False
    assert needs_network_expand(UrlKind.VIDEO, None) is False


def test_format_enqueue_log_single_added() -> None:
    assert format_enqueue_log(1, 1) == "Adicionado à fila."


def test_format_enqueue_log_single_duplicate() -> None:
    assert format_enqueue_log(0, 1) == "URL já está na fila."


def test_format_enqueue_log_playlist_with_skips() -> None:
    msg = format_enqueue_log(2, 4)
    assert "2 vídeo(s) adicionados" in msg
    assert "2 já estavam" in msg


def test_plan_no_videos() -> None:
    plan = plan_resolved_urls([], "download", is_downloading=False)
    assert plan.kind == ResolvedUrlPlanKind.NO_VIDEOS


def test_plan_start_single_video() -> None:
    url = "https://www.youtube.com/watch?v=abc12345678"
    plan = plan_resolved_urls([url], "download", is_downloading=False)
    assert plan.kind == ResolvedUrlPlanKind.START_SINGLE
    assert plan.start_url == url


def test_plan_enqueue_single() -> None:
    url = "https://www.youtube.com/watch?v=abc12345678"
    plan = plan_resolved_urls([url], "enqueue", is_downloading=False)
    assert plan.kind == ResolvedUrlPlanKind.ENQUEUE_ALL
    assert plan.urls_to_enqueue == [url]


def test_plan_enqueue_playlist() -> None:
    urls = [f"https://www.youtube.com/watch?v=id{i:07d}"[:43] for i in range(3)]
    plan = plan_resolved_urls(urls, "enqueue", is_downloading=False)
    assert plan.kind == ResolvedUrlPlanKind.ENQUEUE_ALL
    assert plan.urls_to_enqueue == urls


def test_plan_download_playlist_while_busy_enqueues_all() -> None:
    urls = ["https://www.youtube.com/watch?v=aaaaaaaaaaa", "https://www.youtube.com/watch?v=bbbbbbbbbbb"]
    plan = plan_resolved_urls(urls, "download", is_downloading=True)
    assert plan.kind == ResolvedUrlPlanKind.ENQUEUE_ALL
    assert plan.urls_to_enqueue == urls


def test_plan_download_playlist_idle_starts_first() -> None:
    urls = ["https://www.youtube.com/watch?v=aaaaaaaaaaa", "https://www.youtube.com/watch?v=bbbbbbbbbbb"]
    plan = plan_resolved_urls(urls, "download", is_downloading=False)
    assert plan.kind == ResolvedUrlPlanKind.START_FIRST_ENQUEUE_REST
    assert plan.start_url == urls[0]
    assert plan.urls_to_enqueue == [urls[1]]


def test_format_playlist_download_start_log_multi() -> None:
    msg = format_playlist_download_start_log(5, added_rest=4, skipped=0)
    assert "5 vídeos" in msg
    assert "4 na fila" in msg


def test_format_playlist_download_start_log_single() -> None:
    assert format_playlist_download_start_log(1, added_rest=0, skipped=0) == (
        "Playlist: 1 vídeo — iniciando."
    )
