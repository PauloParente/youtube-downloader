from youtube_downloader.core.text_utils import strip_ansi, truncate_text


def test_strip_ansi_removes_color_codes() -> None:
    raw = "vel: \x1b[0;32m8.7 MiB/s\x1b[0m"
    assert strip_ansi(raw) == "vel: 8.7 MiB/s"
    assert "\x1b" not in strip_ansi(raw)


def test_truncate_text_short_unchanged() -> None:
    assert truncate_text("hello", 10) == "hello"


def test_truncate_text_long_adds_suffix() -> None:
    result = truncate_text("a" * 60, 50)
    assert result.endswith("…")
    assert len(result) == 50
