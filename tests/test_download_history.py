from datetime import datetime, timedelta
from pathlib import Path

import youtube_downloader.core.download_history as history_mod
from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    add_history_entry,
    format_file_size,
    format_relative_date,
    load_history,
    remove_history_entry,
    save_history,
)


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


def test_remove_history_entry(tmp_path: Path, monkeypatch) -> None:
    history_file = tmp_path / "history.json"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", history_file)

    a = DownloadHistoryEntry(
        title="Video A",
        filepath="/tmp/a.mp4",
        completed_at="2026-01-01T12:00:00",
        format_ext="MP4",
        size_bytes=100,
        is_audio=False,
    )
    b = DownloadHistoryEntry(
        title="Video B",
        filepath="/tmp/b.mp4",
        completed_at="2026-01-02T12:00:00",
        format_ext="MP4",
        size_bytes=200,
        is_audio=False,
    )
    save_history([a, b])

    remaining = remove_history_entry("/tmp/a.mp4")

    assert len(remaining) == 1
    assert remaining[0].filepath == "/tmp/b.mp4"
    loaded = load_history()
    assert len(loaded) == 1
    assert loaded[0].filepath == "/tmp/b.mp4"


def test_remove_history_entry_unknown_path(tmp_path: Path, monkeypatch) -> None:
    history_file = tmp_path / "history.json"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", history_file)

    entry = DownloadHistoryEntry(
        title="Video",
        filepath="/tmp/only.mp4",
        completed_at="2026-01-01T12:00:00",
        format_ext="MP4",
        size_bytes=100,
        is_audio=False,
    )
    add_history_entry(entry)

    remaining = remove_history_entry("/tmp/missing.mp4")

    assert len(remaining) == 1
    assert remaining[0].filepath == "/tmp/only.mp4"
