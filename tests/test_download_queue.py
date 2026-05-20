from youtube_downloader.core.download_queue import DownloadQueue


def test_queue_fifo_dedupes() -> None:
    q = DownloadQueue()
    q.add("https://youtu.be/a")
    q.add("https://youtu.be/a")
    q.add("https://youtu.be/b")
    assert len(q) == 2
    assert q.pop_next() == "https://youtu.be/a"
    assert q.pop_next() == "https://youtu.be/b"
    assert q.pop_next() is None
