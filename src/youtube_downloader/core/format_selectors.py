"""yt-dlp format strings by quality and export profile."""

from youtube_downloader.config import QUALITY_FORMATS, QUALITY_OPTIONS

EXPORT_PROFILE_COMPATIBLE = "compatible"
EXPORT_PROFILE_MAX_QUALITY = "max_quality"
VALID_EXPORT_PROFILES = (EXPORT_PROFILE_COMPATIBLE, EXPORT_PROFILE_MAX_QUALITY)

_QUALITY_HEIGHT: dict[str, int | None] = {
    "Melhor disponível": None,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
}


def _height_filter(quality: str) -> str:
    height = _QUALITY_HEIGHT.get(quality)
    if height is None:
        return ""
    return f"[height<={height}]"


def _compatible_mp4(quality: str) -> str:
    h = _height_filter(quality)
    return (
        f"bestvideo[vcodec^=avc1]{h}+bestaudio[acodec^=mp4a]"
        f"/bestvideo[vcodec^=avc1]{h}+bestaudio"
        f"/bestvideo{h}+bestaudio"
        f"/best{h}"
    )


def _compatible_webm(quality: str) -> str:
    h = _height_filter(quality)
    return (
        f"bestvideo[vcodec^=vp9]{h}+bestaudio[acodec^=opus]"
        f"/bestvideo[vcodec^=vp9]{h}+bestaudio"
        f"/bestvideo{h}+bestaudio"
        f"/best{h}"
    )


def build_video_format_string(
    quality: str,
    export_profile: str,
    *,
    video_format: str = "mp4",
) -> str:
    """Build yt-dlp -f selector for video downloads."""
    if quality not in QUALITY_OPTIONS:
        quality = QUALITY_OPTIONS[0]

    if export_profile != EXPORT_PROFILE_COMPATIBLE:
        return QUALITY_FORMATS.get(quality, QUALITY_FORMATS["Melhor disponível"])

    if video_format == "webm":
        return _compatible_webm(quality)
    return _compatible_mp4(quality)
