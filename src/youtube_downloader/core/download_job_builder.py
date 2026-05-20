"""Build DownloadJob from UI fields and persisted AppSettings."""

from youtube_downloader.core.models import DownloadJob
from youtube_downloader.core.settings import AppSettings


def subtitle_languages_for_ui_language(language: str) -> list[str]:
    if language == "en":
        return ["en", "en-US", "en-GB"]
    return ["pt", "pt-BR", "por"]


def build_download_job(
    *,
    url: str,
    output_dir: str,
    quality: str,
    audio_only: bool,
    preferences: AppSettings,
) -> DownloadJob:
    """Merge per-download UI choices with advanced options from settings."""
    return DownloadJob(
        url=url,
        output_dir=output_dir,
        quality=quality,
        audio_only=audio_only,
        video_format=preferences.video_format,
        export_profile=preferences.export_profile,
        audio_bitrate=preferences.audio_bitrate,
        bandwidth_limit_kbps=preferences.bandwidth_limit_kbps,
        auto_download_subtitles=preferences.auto_download_subtitles,
        notify_on_complete=preferences.notify_on_complete,
        ui_language=preferences.language,
        cookies_file=preferences.cookies_file,
    )
