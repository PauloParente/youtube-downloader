from youtube_downloader.config import QUALITY_FORMATS
from youtube_downloader.core.format_selectors import (
    EXPORT_PROFILE_COMPATIBLE,
    EXPORT_PROFILE_MAX_QUALITY,
    build_video_format_string,
)


def test_compatible_mp4_prefers_h264() -> None:
    fmt = build_video_format_string(
        "1080p", EXPORT_PROFILE_COMPATIBLE, video_format="mp4"
    )
    assert "vcodec^=avc1" in fmt
    assert "acodec^=mp4a" in fmt
    assert fmt.split("/")[0].startswith("bestvideo")


def test_compatible_webm_prefers_vp9() -> None:
    fmt = build_video_format_string(
        "720p", EXPORT_PROFILE_COMPATIBLE, video_format="webm"
    )
    assert "vcodec^=vp9" in fmt
    assert "height<=720" in fmt


def test_max_quality_matches_config() -> None:
    for quality, expected in QUALITY_FORMATS.items():
        fmt = build_video_format_string(
            quality, EXPORT_PROFILE_MAX_QUALITY, video_format="mp4"
        )
        assert fmt == expected
        first = fmt.split("/")[0]
        assert first.startswith("bestvideo")
        assert "best[" not in first


def test_max_quality_unknown_quality_falls_back() -> None:
    fmt = build_video_format_string(
        "4K", EXPORT_PROFILE_MAX_QUALITY, video_format="mp4"
    )
    assert fmt == QUALITY_FORMATS["Melhor disponível"]
