"""humanize_ytdlp_error."""

from youtube_downloader.core.download_errors import humanize_ytdlp_error


def test_not_available() -> None:
    raw = "ERROR: [youtube] abc: This video is not available"
    assert humanize_ytdlp_error(raw) == "Este vídeo não está disponível no YouTube."


def test_sign_in() -> None:
    assert "login" in humanize_ytdlp_error("Sign in to confirm your age").casefold()


def test_ffmpeg() -> None:
    assert "FFmpeg" in humanize_ytdlp_error("FFmpeg not found")


def test_private() -> None:
    assert humanize_ytdlp_error("Private video") == "Vídeo privado ou restrito."


def test_empty_fallback() -> None:
    assert humanize_ytdlp_error("") == "Não foi possível concluir o download."
