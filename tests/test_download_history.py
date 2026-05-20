from datetime import datetime, timedelta
from pathlib import Path

import youtube_downloader.core.download_history as history_mod
from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    add_history_entry,
    clear_history,
    format_file_size,
    format_relative_date,
    history_thumbnail_path_for_url,
    load_history,
    refresh_entries_from_disk,
    remove_history_entry,
    save_history,
    save_history_thumbnail,
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


def test_clear_history(tmp_path: Path, monkeypatch) -> None:
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
    save_history([entry])

    result = clear_history()

    assert result == []
    assert load_history() == []


def test_refresh_entries_from_disk_existing(tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"x" * 2048)

    entry = DownloadHistoryEntry(
        title="Clip",
        filepath=str(media),
        completed_at="2025-06-01T10:00:00",
        format_ext="MP4",
        size_bytes=1,
        is_audio=False,
        source_url="https://example.com/watch?v=1",
    )

    refreshed = refresh_entries_from_disk([entry])

    assert len(refreshed) == 1
    assert refreshed[0].completed_at == "2025-06-01T10:00:00"
    assert refreshed[0].title == "Clip"
    assert refreshed[0].size_bytes == 2048
    assert refreshed[0].source_url == "https://example.com/watch?v=1"


def test_refresh_entries_from_disk_missing(tmp_path: Path) -> None:
    entry = DownloadHistoryEntry(
        title="Gone",
        filepath=str(tmp_path / "missing.mp4"),
        completed_at="2025-06-01T10:00:00",
        format_ext="MP4",
        size_bytes=999,
        is_audio=False,
    )

    refreshed = refresh_entries_from_disk([entry])

    assert refreshed[0].size_bytes == 0
    assert refreshed[0].title == "Gone"
    assert refreshed[0].completed_at == "2025-06-01T10:00:00"


def test_save_history_thumbnail(tmp_path: Path, monkeypatch) -> None:
    from io import BytesIO

    from PIL import Image

    thumb_dir = tmp_path / "cache" / "history"
    monkeypatch.setattr(history_mod, "HISTORY_THUMB_DIR", thumb_dir)

    url = "https://www.youtube.com/watch?v=abc123"
    buf = BytesIO()
    Image.new("RGB", (4, 4), color=(10, 20, 30)).save(buf, format="JPEG")
    saved = save_history_thumbnail(url, buf.getvalue())

    assert saved
    assert Path(saved).is_file()
    assert history_thumbnail_path_for_url(url) == Path(saved)
