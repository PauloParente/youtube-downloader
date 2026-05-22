"""Persist user preferences beside the executable / project root."""

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from youtube_downloader.config import DEFAULT_DOWNLOADS_DIR, PROJECT_ROOT, QUALITY_OPTIONS
from youtube_downloader.core.format_selectors import (
    EXPORT_PROFILE_COMPATIBLE,
    VALID_EXPORT_PROFILES,
)
from youtube_downloader.core.logging_config import get_logger

logger = get_logger("settings")

SETTINGS_FILE = PROJECT_ROOT / "settings.json"


@dataclass
class AppSettings:
    output_dir: str
    quality: str
    audio_only: bool
    language: str = "pt-BR"
    video_format: str = "mp4"
    export_profile: str = EXPORT_PROFILE_COMPATIBLE
    audio_bitrate: str = "192"
    bandwidth_limit_kbps: int = 0
    notify_on_complete: bool = True
    auto_download_subtitles: bool = False
    appearance_mode: str = "dark"
    cookies_file: str = ""
    activity_log_expanded: bool = True
    sidebar_collapsed: bool = False
    focus_queue_on_download: bool = True

    @classmethod
    def defaults(cls) -> "AppSettings":
        return cls(
            output_dir=str(DEFAULT_DOWNLOADS_DIR),
            quality=QUALITY_OPTIONS[0],
            audio_only=False,
            language="pt-BR",
            video_format="mp4",
            export_profile=EXPORT_PROFILE_COMPATIBLE,
            audio_bitrate="192",
            bandwidth_limit_kbps=0,
            notify_on_complete=True,
            auto_download_subtitles=False,
            appearance_mode="dark",
            cookies_file="",
            activity_log_expanded=True,
            sidebar_collapsed=False,
            focus_queue_on_download=True,
        )


_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:[/\\]")


def _looks_like_windows_absolute(text: str) -> bool:
    return bool(_WINDOWS_ABS_RE.match(text.strip()))


def _resolve_output_dir(raw: str) -> str:
    """Caminho absoluto gravável ao lado do .exe; ignora pastas de outro PC ou inacessíveis."""
    default = PROJECT_ROOT / "downloads"
    text = (raw or "").strip()
    if not text:
        candidate = default
    elif os.name != "nt" and _looks_like_windows_absolute(text):
        logger.warning(
            "output_dir estilo Windows em %s; usando %s",
            text,
            default,
        )
        default.mkdir(parents=True, exist_ok=True)
        return str(default.resolve())
    else:
        candidate = Path(text)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate

    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return str(candidate.resolve())
    except OSError as exc:
        logger.warning(
            "output_dir invalida ou sem permissao (%s): %s; usando %s",
            text or raw,
            exc,
            default,
        )
        default.mkdir(parents=True, exist_ok=True)
        return str(default.resolve())


def _coerce_settings(data: dict[str, Any]) -> AppSettings:
    defaults = AppSettings.defaults()
    quality = data.get("quality", defaults.quality)
    if quality not in QUALITY_OPTIONS:
        quality = defaults.quality
    language = str(data.get("language", defaults.language))
    if language not in ("pt-BR", "en"):
        language = defaults.language
    video_format = str(data.get("video_format", defaults.video_format))
    if video_format not in ("mp4", "webm"):
        video_format = defaults.video_format
    audio_bitrate = str(data.get("audio_bitrate", defaults.audio_bitrate))
    if audio_bitrate not in ("128", "192", "320"):
        audio_bitrate = defaults.audio_bitrate
    try:
        bandwidth = int(data.get("bandwidth_limit_kbps", defaults.bandwidth_limit_kbps))
    except (TypeError, ValueError):
        bandwidth = defaults.bandwidth_limit_kbps
    if bandwidth < 0:
        bandwidth = 0
    appearance = str(data.get("appearance_mode", defaults.appearance_mode))
    if appearance not in ("dark", "light"):
        appearance = defaults.appearance_mode
    cookies_file = str(data.get("cookies_file", defaults.cookies_file)).strip()
    export_profile = str(data.get("export_profile", defaults.export_profile))
    if export_profile not in VALID_EXPORT_PROFILES:
        export_profile = defaults.export_profile

    return AppSettings(
        output_dir=_resolve_output_dir(str(data.get("output_dir", defaults.output_dir))),
        quality=quality,
        audio_only=bool(data.get("audio_only", defaults.audio_only)),
        language=language,
        video_format=video_format,
        export_profile=export_profile,
        audio_bitrate=audio_bitrate,
        bandwidth_limit_kbps=bandwidth,
        notify_on_complete=bool(
            data.get("notify_on_complete", defaults.notify_on_complete)
        ),
        auto_download_subtitles=bool(
            data.get("auto_download_subtitles", defaults.auto_download_subtitles)
        ),
        appearance_mode=appearance,
        cookies_file=cookies_file,
        activity_log_expanded=bool(
            data.get("activity_log_expanded", defaults.activity_log_expanded)
        ),
        sidebar_collapsed=bool(
            data.get("sidebar_collapsed", defaults.sidebar_collapsed)
        ),
        focus_queue_on_download=bool(
            data.get("focus_queue_on_download", defaults.focus_queue_on_download)
        ),
    )


def load_settings() -> AppSettings:
    if not SETTINGS_FILE.is_file():
        return AppSettings.defaults()
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("settings root must be object")
        settings = _coerce_settings(raw)
        logger.info("Configuracoes carregadas de %s", SETTINGS_FILE)
        return settings
    except Exception:
        logger.exception("Falha ao carregar settings.json; usando padroes")
        return AppSettings.defaults()


def save_settings(settings: AppSettings) -> None:
    try:
        SETTINGS_FILE.write_text(
            json.dumps(asdict(settings), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.debug("Configuracoes salvas em %s", SETTINGS_FILE)
    except Exception:
        logger.exception("Falha ao salvar settings.json")
