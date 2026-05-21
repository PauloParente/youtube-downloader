"""User-facing messages for yt-dlp / download failures."""

from __future__ import annotations

from youtube_downloader.core.text_utils import strip_ansi

_GENERIC = "Não foi possível concluir o download."
_FFMPEG = (
    "FFmpeg não encontrado. Use a versão do .exe gerada por build.ps1 "
    "(FFmpeg embutido) ou instale o FFmpeg no sistema."
)

_RULES: list[tuple[tuple[str, ...], str]] = [
    (("not available", "video unavailable"), "Este vídeo não está disponível no YouTube."),
    (("sign in", "login required", "use --cookies"), "Este conteúdo exige login; configure cookies.txt em Configurações."),
    (("private video", "privado", "private"), "Vídeo privado ou restrito."),
    (("ffmpeg",), _FFMPEG),
    (("copyright", "blocked"), "Download bloqueado por restrições do YouTube."),
    (("age", "confirm your age"), "Este vídeo exige confirmação de idade na conta YouTube."),
]


def humanize_ytdlp_error(raw: str) -> str:
    """Map common yt-dlp error substrings to Portuguese UI text."""
    if not raw or not raw.strip():
        return _GENERIC
    text = strip_ansi(raw).strip()
    lower = text.casefold()
    for needles, message in _RULES:
        if any(n in lower for n in needles):
            return message
    if len(text) > 120:
        return text[:117] + "…"
    return text if text else _GENERIC
