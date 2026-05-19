"""Text helpers for UI messages."""

import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color/control sequences from yt-dlp progress strings."""
    return _ANSI_RE.sub("", text).strip()


def truncate_text(text: str, max_len: int = 50, suffix: str = "…") -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    if max_len <= len(suffix):
        return text[:max_len]
    return text[: max_len - len(suffix)] + suffix
