"""Quality presets and application constants."""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Project root in dev; folder containing the .exe when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = get_project_root()
DEFAULT_DOWNLOADS_DIR = PROJECT_ROOT / "downloads"

QUALITY_OPTIONS = [
    "Melhor disponível",
    "1080p",
    "720p",
    "480p",
]

# Rótulos exibidos no ComboBox (valores internos permanecem em QUALITY_OPTIONS).
QUALITY_DISPLAY_LABELS: dict[str, str] = {
    "Melhor disponível": "Melhor disponível",
    "1080p": "1080p (Alta)",
    "720p": "Média (720p)",
    "480p": "480p (Economia)",
}
QUALITY_FROM_DISPLAY: dict[str, str] = {
    label: key for key, label in QUALITY_DISPLAY_LABELS.items()
}
QUALITY_COMBO_VALUES: list[str] = list(QUALITY_DISPLAY_LABELS.values())

# Container final quando vídeo e áudio são baixados separados (yt-dlp FFmpegMergerPP).
VIDEO_MERGE_OUTPUT_FORMAT = "mp4"

QUALITY_FORMATS = {
    # DASH primeiro: MP4 progressivo (ex. itag 18, 360p) não deve vencer 1080p separado.
    "Melhor disponível": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
}

AUDIO_FORMAT = "bestaudio/best"

AUDIO_POSTPROCESSORS = [
    {
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }
]

APP_TITLE = "YouTube Downloader"
APP_VERSION = "1.2.0"
WINDOW_SIZE = "980x720"
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 680
DOWNLOADS_FOOTER_STACK_WIDTH = 720
