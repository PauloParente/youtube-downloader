"""Tests for mapping DownloadJob + settings to yt-dlp options."""

from youtube_downloader.core.downloader import build_ytdl_opts
from youtube_downloader.core.download_job_builder import (
    build_download_job,
    subtitle_languages_for_ui_language,
)
from youtube_downloader.core.models import DownloadJob
from youtube_downloader.core.settings import AppSettings


def _job(**overrides) -> DownloadJob:
    base = dict(
        url="https://www.youtube.com/watch?v=test",
        output_dir="/tmp/out",
        quality="1080p",
        audio_only=False,
    )
    base.update(overrides)
    return DownloadJob(**base)


def test_build_download_job_merges_preferences() -> None:
    prefs = AppSettings(
        output_dir="/defaults",
        quality="720p",
        audio_only=True,
        language="en",
        video_format="webm",
        audio_bitrate="320",
        bandwidth_limit_kbps=500,
        notify_on_complete=False,
        auto_download_subtitles=True,
    )
    job = build_download_job(
        url="https://youtu.be/x",
        output_dir="/dl",
        quality="1080p",
        audio_only=False,
        preferences=prefs,
    )
    assert job.output_dir == "/dl"
    assert job.quality == "1080p"
    assert job.video_format == "webm"
    assert job.export_profile == prefs.export_profile
    assert job.audio_bitrate == "320"
    assert job.bandwidth_limit_kbps == 500
    assert job.auto_download_subtitles is True
    assert job.ui_language == "en"


def test_build_ytdl_opts_video_merge_format_webm() -> None:
    opts = build_ytdl_opts(_job(video_format="webm"), "/usr/bin/ffmpeg")
    assert opts["merge_output_format"] == "webm"


def test_build_ytdl_opts_video_defaults_to_mp4_merge() -> None:
    opts = build_ytdl_opts(_job(video_format="mp4"), "/usr/bin/ffmpeg")
    assert opts["merge_output_format"] == "mp4"


def test_build_ytdl_opts_compatible_profile_uses_h264_selector() -> None:
    opts = build_ytdl_opts(
        _job(export_profile="compatible", video_format="mp4"),
        "/usr/bin/ffmpeg",
    )
    assert "vcodec^=avc1" in opts["format"]


def test_build_ytdl_opts_max_quality_profile_unchanged() -> None:
    opts = build_ytdl_opts(
        _job(export_profile="max_quality", quality="1080p"),
        "/usr/bin/ffmpeg",
    )
    assert opts["format"] == "bestvideo[height<=1080]+bestaudio/best[height<=1080]"


def test_build_ytdl_opts_audio_bitrate_in_postprocessor() -> None:
    opts = build_ytdl_opts(_job(audio_only=True, audio_bitrate="320"), "/usr/bin/ffmpeg")
    assert opts["postprocessors"][0]["preferredquality"] == "320"


def test_build_ytdl_opts_bandwidth_ratelimit() -> None:
    opts = build_ytdl_opts(_job(bandwidth_limit_kbps=800), "/usr/bin/ffmpeg")
    assert opts["ratelimit"] == 800 * 125
    opts_zero = build_ytdl_opts(_job(bandwidth_limit_kbps=0), "/usr/bin/ffmpeg")
    assert "ratelimit" not in opts_zero


def test_build_ytdl_opts_subtitles() -> None:
    opts = build_ytdl_opts(
        _job(auto_download_subtitles=True, ui_language="pt-BR"),
        "/usr/bin/ffmpeg",
    )
    assert opts["writesubtitles"] is True
    assert opts["writeautomaticsub"] is True
    assert "pt-BR" in opts["subtitleslangs"]


def test_subtitle_languages_for_ui_language() -> None:
    assert "en" in subtitle_languages_for_ui_language("en")
    assert "pt-BR" in subtitle_languages_for_ui_language("pt-BR")


def test_build_ytdl_opts_cookies_file(tmp_path) -> None:
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    opts = build_ytdl_opts(
        _job(cookies_file=str(cookies)),
        "/usr/bin/ffmpeg",
    )
    assert opts["cookiefile"] == str(cookies)


def test_build_ytdl_opts_skips_missing_cookies() -> None:
    opts = build_ytdl_opts(_job(cookies_file="/nope/cookies.txt"), "/usr/bin/ffmpeg")
    assert "cookiefile" not in opts


def test_build_ytdl_opts_always_noplaylist() -> None:
    opts = build_ytdl_opts(_job(), "/usr/bin/ffmpeg")
    assert opts["noplaylist"] is True
