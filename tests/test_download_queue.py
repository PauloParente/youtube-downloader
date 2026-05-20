from youtube_downloader.core.download_queue import DownloadQueue


def test_queue_fifo_dedupes() -> None:
    q = DownloadQueue()
    assert q.add("https://youtu.be/a") is True
    assert q.add("https://youtu.be/a") is False
    assert q.add("https://youtu.be/b") is True
    assert len(q) == 2
    assert q.pop_next() == "https://youtu.be/a"
    assert q.pop_next() == "https://youtu.be/b"
    assert q.pop_next() is None


def test_add_rejects_empty() -> None:
    q = DownloadQueue()
    assert q.add("   ") is False
    assert len(q) == 0


def test_remove_at() -> None:
    q = DownloadQueue()
    q.add("https://youtu.be/a")
    q.add("https://youtu.be/b")
    q.add("https://youtu.be/c")
    assert q.remove_at(1) is True
    assert q.snapshot() == ["https://youtu.be/a", "https://youtu.be/c"]
    assert q.remove_at(99) is False


def test_clear() -> None:
    q = DownloadQueue()
    q.add("https://youtu.be/a")
    q.clear()
    assert len(q) == 0
    assert q.snapshot() == []
