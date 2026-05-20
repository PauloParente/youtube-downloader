"""Tests for playlist URL classification and expansion (offline mocks)."""

from unittest.mock import MagicMock, patch

import pytest

from youtube_downloader.core.playlist_urls import (
    PlaylistExpandError,
    UrlKind,
    classify_youtube_url,
    expand_playlist_urls,
    is_valid_video_id,
    playlist_page_url,
    resolve_download_urls,
    watch_url_for_video_id,
)


def test_classify_video_watch() -> None:
    assert (
        classify_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        == UrlKind.VIDEO
    )


def test_classify_playlist_page() -> None:
    assert (
        classify_youtube_url("https://www.youtube.com/playlist?list=PLabc123")
        == UrlKind.PLAYLIST
    )


def test_classify_video_in_playlist() -> None:
    assert (
        classify_youtube_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc123"
        )
        == UrlKind.VIDEO_IN_PLAYLIST
    )


def test_watch_url_for_video_id() -> None:
    assert watch_url_for_video_id("abc123XYZ01") == (
        "https://www.youtube.com/watch?v=abc123XYZ01"
    )


def test_resolve_single_video() -> None:
    urls = resolve_download_urls("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert urls == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]


def test_resolve_video_in_playlist_single_mode() -> None:
    url = "https://www.youtube.com/watch?v=vid11111111&list=PLtest"
    urls = resolve_download_urls(url, playlist_mode="single")
    assert urls == ["https://www.youtube.com/watch?v=vid11111111"]


def test_resolve_video_in_playlist_requires_mode() -> None:
    with pytest.raises(ValueError):
        resolve_download_urls(
            "https://www.youtube.com/watch?v=vid11111111&list=PLtest"
        )


def test_playlist_page_url_from_watch_and_list() -> None:
    url = (
        "https://www.youtube.com/watch?v=THZx5JLH-rE"
        "&list=PLbK79OJUFFXzHnu_mMae2XK9wv9NcCZTe"
    )
    assert playlist_page_url(url) == (
        "https://www.youtube.com/playlist?list=PLbK79OJUFFXzHnu_mMae2XK9wv9NcCZTe"
    )


def test_is_valid_video_id_rejects_playlist_id() -> None:
    assert is_valid_video_id("THZx5JLH-rE") is True
    assert is_valid_video_id("PLbK79OJUFFXzHnu_mMae2XK9wv9NcCZTe") is False


@patch("youtube_downloader.core.playlist_urls.yt_dlp.YoutubeDL")
def test_expand_watch_with_list_uses_playlist_url(mock_ydl_cls: MagicMock) -> None:
    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl
    mock_ydl.__exit__.return_value = False
    mock_ydl.extract_info.return_value = {
        "entries": [{"id": "THZx5JLH-rE"}, {"id": "abc12345678"}],
    }
    mock_ydl_cls.return_value = mock_ydl

    watch_url = (
        "https://www.youtube.com/watch?v=THZx5JLH-rE"
        "&list=PLbK79OJUFFXzHnu_mMae2XK9wv9NcCZTe"
    )
    urls = expand_playlist_urls(watch_url)

    mock_ydl.extract_info.assert_called_once_with(
        "https://www.youtube.com/playlist?list=PLbK79OJUFFXzHnu_mMae2XK9wv9NcCZTe",
        download=False,
    )
    assert len(urls) == 2
    assert "PLbK79" not in urls[0]


@patch("youtube_downloader.core.playlist_urls.yt_dlp.YoutubeDL")
def test_expand_skips_invalid_entry_ids(mock_ydl_cls: MagicMock) -> None:
    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl
    mock_ydl.__exit__.return_value = False
    mock_ydl.extract_info.return_value = {
        "entries": [
            {"id": "PLbK79OJUFFXzHnu_mMae2XK9wv9NcCZTe"},
            {"id": "aaa11111111"},
        ],
    }
    mock_ydl_cls.return_value = mock_ydl

    urls = expand_playlist_urls("https://www.youtube.com/playlist?list=PLx")
    assert urls == ["https://www.youtube.com/watch?v=aaa11111111"]


@patch("youtube_downloader.core.playlist_urls.yt_dlp.YoutubeDL")
def test_expand_playlist_urls(mock_ydl_cls: MagicMock) -> None:
    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl
    mock_ydl.__exit__.return_value = False
    mock_ydl.extract_info.return_value = {
        "entries": [
            {"id": "aaa11111111"},
            {"id": "bbb22222222"},
            {"id": "aaa11111111"},
        ],
    }
    mock_ydl_cls.return_value = mock_ydl

    urls = expand_playlist_urls("https://www.youtube.com/playlist?list=PLx")
    assert urls == [
        "https://www.youtube.com/watch?v=aaa11111111",
        "https://www.youtube.com/watch?v=bbb22222222",
    ]


@patch("youtube_downloader.core.playlist_urls.yt_dlp.YoutubeDL")
def test_expand_playlist_empty_raises(mock_ydl_cls: MagicMock) -> None:
    mock_ydl = MagicMock()
    mock_ydl.__enter__.return_value = mock_ydl
    mock_ydl.__exit__.return_value = False
    mock_ydl.extract_info.return_value = {"entries": []}
    mock_ydl_cls.return_value = mock_ydl

    with pytest.raises(PlaylistExpandError):
        expand_playlist_urls("https://www.youtube.com/playlist?list=PLempty")


@patch("youtube_downloader.core.playlist_urls.expand_playlist_urls")
def test_resolve_playlist_full(mock_expand: MagicMock) -> None:
    mock_expand.return_value = [
        "https://www.youtube.com/watch?v=one11111111",
        "https://www.youtube.com/watch?v=two22222222",
    ]
    urls = resolve_download_urls("https://www.youtube.com/playlist?list=PLx")
    assert len(urls) == 2
    mock_expand.assert_called_once()
