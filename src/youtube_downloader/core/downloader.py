"""yt-dlp wrapper with progress hooks and cancellation support."""

import copy
import os
import re
import threading
import time
from typing import Callable, Optional

import yt_dlp

from youtube_downloader.config import (
    AUDIO_FORMAT,
    AUDIO_POSTPROCESSORS,
    QUALITY_FORMATS,
)
from youtube_downloader.core.download_job_builder import subtitle_languages_for_ui_language
from youtube_downloader.core.ffmpeg_utils import (
    ffmpeg_available as is_ffmpeg_available,
    find_ffmpeg_dir,
)
from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.text_utils import strip_ansi, truncate_text

logger = get_logger("downloader")

_PROGRESS_THROTTLE_SEC = 0.4

def _merge_status_message(job: DownloadJob) -> str:
    if job.audio_only:
        return "Convertendo áudio…"
    fmt = job.video_format.upper() if job.video_format in ("mp4", "webm") else "MP4"
    return f"Mesclando vídeo e áudio em {fmt}…"

_INTERMEDIATE_FRAGMENT_RE = re.compile(r"\.f\d+\.", re.IGNORECASE)
_ORPHAN_FRAGMENT_RE = re.compile(r"\.f\d+\.[^.]+$", re.IGNORECASE)

_KBPS_TO_BYTES_PER_SEC = 125  # 1 kbps ≈ 125 bytes/s for yt-dlp ratelimit


def build_ytdl_opts(job: DownloadJob, ffmpeg_dir: str) -> dict:
    """Build yt-dlp options from a download job (testable, no network)."""
    format_string = AUDIO_FORMAT if job.audio_only else QUALITY_FORMATS.get(
        job.quality, QUALITY_FORMATS["Melhor disponível"]
    )

    opts: dict = {
        "outtmpl": os.path.join(job.output_dir, "%(title)s.%(ext)s"),
        "format": format_string,
        "ffmpeg_location": ffmpeg_dir,
        "noplaylist": not job.download_playlist,
        "ignoreerrors": False,
        "quiet": True,
        "no_warnings": True,
        "color": "never",
        "restrictfilenames": True,
        "windowsfilenames": True,
    }

    if job.bandwidth_limit_kbps > 0:
        opts["ratelimit"] = job.bandwidth_limit_kbps * _KBPS_TO_BYTES_PER_SEC

    if job.audio_only:
        postprocessors = copy.deepcopy(AUDIO_POSTPROCESSORS)
        postprocessors[0]["preferredquality"] = job.audio_bitrate
        opts["postprocessors"] = postprocessors
    else:
        merge_format = job.video_format if job.video_format in ("mp4", "webm") else "mp4"
        opts["merge_output_format"] = merge_format

    if job.auto_download_subtitles:
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        opts["subtitleslangs"] = subtitle_languages_for_ui_language(job.ui_language)
        opts["subtitlesformat"] = "best"

    if job.cookies_file and os.path.isfile(job.cookies_file):
        opts["cookiefile"] = job.cookies_file

    return opts


class DownloadCancelled(Exception):
    """Raised when the user cancels an in-progress download."""


class YoutubeDownloader:
    def __init__(self) -> None:
        self._cancel = threading.Event()
        self._current_title: Optional[str] = None
        self._current_job: Optional[DownloadJob] = None
        self._last_filepath: Optional[str] = None
        self._playlist_completed = 0
        self._playlist_total: Optional[int] = None
        self._last_playlist_index: Optional[int] = None

    def cancel(self) -> None:
        self._cancel.set()

    def reset(self) -> None:
        self._cancel.clear()
        self._current_title = None
        self._current_job = None
        self._last_filepath = None
        self._playlist_completed = 0
        self._playlist_total = None
        self._last_playlist_index = None

    @staticmethod
    def ffmpeg_available() -> bool:
        return is_ffmpeg_available()

    @staticmethod
    def _is_intermediate_fragment(filename: str) -> bool:
        return bool(_INTERMEDIATE_FRAGMENT_RE.search(os.path.basename(filename)))

    @staticmethod
    def _log_selected_formats(url: str, opts: dict) -> None:
        """Registra format_id/height escolhidos pelo seletor yt-dlp (diagnóstico)."""
        probe_opts = {**opts, "quiet": True, "no_warnings": True}
        try:
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            logger.warning("Não foi possível inspecionar formatos: %s", exc)
            return

        requested = info.get("requested_formats")
        if requested:
            parts = []
            for fmt in requested:
                height = fmt.get("height")
                height_label = f"{height}p" if height else "?"
                parts.append(
                    f"{fmt.get('format_id')} ({fmt.get('ext')}, {height_label})"
                )
            logger.info("Formatos selecionados (DASH): %s", " + ".join(parts))
            return

        fmt = info.get("format") or {}
        height = fmt.get("height")
        height_label = f"{height}p" if height else "?"
        logger.info(
            "Formato selecionado: id=%s ext=%s height=%s",
            fmt.get("format_id"),
            fmt.get("ext"),
            height_label,
        )

    @staticmethod
    def _find_merge_orphans(output_dir: str) -> list[str]:
        if not os.path.isdir(output_dir):
            return []
        return [
            os.path.join(output_dir, name)
            for name in os.listdir(output_dir)
            if _ORPHAN_FRAGMENT_RE.search(name)
        ]

    def _emit_playlist_progress(
        self, on_event: Callable[[ProgressEvent], None]
    ) -> None:
        if self._playlist_total is None or self._playlist_total < 2:
            return
        on_event(
            ProgressEvent(
                event_type=EventType.PROGRESS,
                message=(
                    f"Playlist: {self._playlist_completed}/"
                    f"{self._playlist_total} concluídos"
                ),
                playlist_completed=self._playlist_completed,
                playlist_total=self._playlist_total,
                title=self._current_title,
            )
        )

    def download(
        self,
        job: DownloadJob,
        on_event: Callable[[ProgressEvent], None],
    ) -> None:
        self.reset()

        logger.info(
            "Download iniciado: url=%s pasta=%s qualidade=%s audio_only=%s playlist=%s "
            "formato=%s bitrate=%s banda_kbps=%s legendas=%s",
            job.url,
            job.output_dir,
            job.quality,
            job.audio_only,
            job.download_playlist,
            job.video_format,
            job.audio_bitrate,
            job.bandwidth_limit_kbps,
            job.auto_download_subtitles,
        )

        ffmpeg_dir = find_ffmpeg_dir()
        if not ffmpeg_dir:
            logger.error("FFmpeg não encontrado para download: %s", job.url)
            on_event(
                ProgressEvent(
                    event_type=EventType.ERROR,
                    message=(
                        "FFmpeg não encontrado. Use a versão do .exe gerada por build.ps1 "
                        "(FFmpeg embutido) ou instale o FFmpeg no sistema."
                    ),
                )
            )
            return

        self._current_job = job
        progress_hook = self._make_hook(on_event, job)
        opts = build_ytdl_opts(job, ffmpeg_dir)
        opts["progress_hooks"] = [progress_hook]
        opts["postprocessor_hooks"] = [self._make_postprocessor_hook(on_event)]

        try:
            if not job.audio_only:
                self._log_selected_formats(job.url, opts)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([job.url])
            if self._cancel.is_set():
                logger.info("Download cancelado (usuario): %s", job.url)
                on_event(
                    ProgressEvent(
                        event_type=EventType.CANCELLED,
                        message="Download cancelado.",
                    )
                )
            else:
                done_message = "Download concluído com sucesso."
                if not job.audio_only:
                    orphans = self._find_merge_orphans(job.output_dir)
                    if orphans:
                        logger.error(
                            "Mesclagem incompleta; arquivos parciais: %s",
                            orphans,
                        )
                        done_message = (
                            "Download concluído em partes separadas — verifique o "
                            "FFmpeg ou tente outra qualidade."
                        )
                logger.info("Download concluído: %s", job.url)
                on_event(
                    ProgressEvent(
                        event_type=EventType.DONE,
                        message=done_message,
                        percent=1.0,
                        filepath=self._last_filepath,
                        playlist_completed=self._playlist_completed,
                        playlist_total=self._playlist_total,
                    )
                )
        except DownloadCancelled:
            logger.info("Download cancelado (hook): %s", job.url)
            on_event(
                ProgressEvent(
                    event_type=EventType.CANCELLED,
                    message="Download cancelado.",
                )
            )
        except Exception as exc:
            if self._cancel.is_set():
                logger.info("Download cancelado com exceção: %s", job.url)
                on_event(
                    ProgressEvent(
                        event_type=EventType.CANCELLED,
                        message="Download cancelado.",
                    )
                )
            else:
                logger.error("Download falhou: %s | %s", job.url, exc)
                logger.exception("Detalhes do download falhou")
                on_event(
                    ProgressEvent(
                        event_type=EventType.ERROR,
                        message=str(exc),
                    )
                )

    def _format_progress_message(
        self, data: dict, percent: Optional[float]
    ) -> str:
        info = data.get("info_dict") or {}
        prefix = ""
        playlist_index = info.get("playlist_index")
        playlist_count = info.get("playlist_count")
        if playlist_index is not None and playlist_count:
            prefix = f"Vídeo {playlist_index}/{playlist_count} · "

        title = truncate_text(self._current_title or "…", 50)
        detail_parts: list[str] = []
        if percent is not None:
            detail_parts.append(f"{percent * 100:.1f}%")

        speed = strip_ansi(data.get("_speed_str") or "")
        if speed:
            detail_parts.append(speed)

        eta = strip_ansi(data.get("_eta_str") or "")
        if eta:
            detail_parts.append(f"{eta} restantes")

        if detail_parts:
            return f"{prefix}Baixando: {title} — " + " · ".join(detail_parts)
        return f"{prefix}Baixando: {title}…"

    def _emit_merge_status(self, on_event: Callable[[ProgressEvent], None]) -> None:
        job = self._current_job
        message = _merge_status_message(job) if job else "Mesclando vídeo e áudio…"
        on_event(
            ProgressEvent(
                event_type=EventType.LOG,
                message=message,
            )
        )
        on_event(
            ProgressEvent(
                event_type=EventType.PROGRESS,
                message=message,
            )
        )

    def _make_postprocessor_hook(
        self, on_event: Callable[[ProgressEvent], None]
    ) -> Callable[[dict], None]:
        merge_status_active = False

        def hook(data: dict) -> None:
            nonlocal merge_status_active

            if self._cancel.is_set():
                raise DownloadCancelled()

            postprocessor = data.get("postprocessor", "")
            status = data.get("status")

            if postprocessor != "Merger":
                return

            if status == "started":
                merge_status_active = True
                logger.info("Mesclagem video+audio iniciada")
                self._emit_merge_status(on_event)
            elif status == "finished":
                merge_status_active = False
                info = data.get("info_dict") or {}
                filepath = info.get("filepath")
                if filepath and os.path.isfile(filepath):
                    self._last_filepath = filepath
            elif status == "processing" and not merge_status_active:
                merge_status_active = True
                self._emit_merge_status(on_event)

        return hook

    def _make_hook(
        self,
        on_event: Callable[[ProgressEvent], None],
        job: DownloadJob,
    ) -> Callable[[dict], None]:
        last_progress_emit = 0.0

        def hook(data: dict) -> None:
            nonlocal last_progress_emit

            if self._cancel.is_set():
                raise DownloadCancelled()

            status = data.get("status")
            info = data.get("info_dict") or {}

            if status == "downloading":
                title = info.get("title") or self._current_title
                if title:
                    self._current_title = title

                playlist_count = info.get("playlist_count")
                if playlist_count and job.download_playlist:
                    self._playlist_total = int(playlist_count)

                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                percent: Optional[float] = None
                if total and total > 0:
                    percent = min(downloaded / total, 1.0)

                now = time.monotonic()
                force_emit = percent is not None and percent >= 0.99
                if (
                    not force_emit
                    and (now - last_progress_emit) < _PROGRESS_THROTTLE_SEC
                ):
                    return
                last_progress_emit = now

                on_event(
                    ProgressEvent(
                        event_type=EventType.PROGRESS,
                        message=self._format_progress_message(data, percent),
                        percent=percent,
                        title=self._current_title,
                        playlist_completed=self._playlist_completed,
                        playlist_total=self._playlist_total,
                    )
                )

            elif status == "finished":
                filename = data.get("filename", "")
                basename = os.path.basename(filename)
                if self._is_intermediate_fragment(filename):
                    on_event(
                        ProgressEvent(
                            event_type=EventType.PROGRESS,
                            message="Baixando faixas de vídeo/áudio…",
                            title=self._current_title,
                            playlist_completed=self._playlist_completed,
                            playlist_total=self._playlist_total,
                        )
                    )
                else:
                    if filename and os.path.isfile(filename):
                        self._last_filepath = filename
                    playlist_index = info.get("playlist_index")
                    if (
                        job.download_playlist
                        and self._playlist_total
                        and self._playlist_total >= 2
                        and playlist_index is not None
                        and playlist_index != self._last_playlist_index
                    ):
                        self._last_playlist_index = int(playlist_index)
                        self._playlist_completed = self._last_playlist_index
                        self._emit_playlist_progress(on_event)
                    on_event(
                        ProgressEvent(
                            event_type=EventType.LOG,
                            message=f"Processando: {basename}",
                            percent=1.0,
                            title=self._current_title,
                            playlist_completed=self._playlist_completed,
                            playlist_total=self._playlist_total,
                            filepath=filename or None,
                        )
                    )

        return hook
