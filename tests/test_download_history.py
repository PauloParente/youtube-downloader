from datetime import datetime, timedelta

from youtube_downloader.core.download_history import format_file_size, format_relative_date


def test_format_file_size() -> None:
    assert format_file_size(450 * 1024 * 1024) == "450 MB"
    assert format_file_size(0) == "0 B"


def test_format_relative_date_today() -> None:
    now = datetime.now()
    label = format_relative_date(now.isoformat(timespec="seconds"))
    assert label.startswith("Hoje,")


def test_format_relative_date_yesterday() -> None:
    yesterday = datetime.now() - timedelta(days=1)
    label = format_relative_date(yesterday.isoformat(timespec="seconds"))
    assert label.startswith("Ontem,")
