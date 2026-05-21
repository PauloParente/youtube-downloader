"""Text helpers for UI messages."""

import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color/control sequences from yt-dlp progress strings."""
    return _ANSI_RE.sub("", text).strip()


_URL_IN_TEXT_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]+|youtu\.be/[^\s]+)",
    re.IGNORECASE,
)


def extract_url_from_drop_text(text: str) -> str:
    """First YouTube watch/short URL from plain text or file:// URI list."""
    if not text:
        return ""
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("file://"):
            continue
        match = _URL_IN_TEXT_RE.search(line)
        if match:
            return match.group(0).rstrip(".,;)")
    match = _URL_IN_TEXT_RE.search(text)
    if match:
        return match.group(0).rstrip(".,;)")
    return ""


def truncate_text(text: str, max_len: int = 50, suffix: str = "…") -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    if max_len <= len(suffix):
        return text[:max_len]
    return text[: max_len - len(suffix)] + suffix
