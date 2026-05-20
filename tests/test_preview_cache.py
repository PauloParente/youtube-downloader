"""Tests for PreviewCache dedupe and storage."""

from unittest.mock import patch

from PIL import Image

from youtube_downloader.core.metadata import VideoPreview
from youtube_downloader.core.preview_cache import PreviewCache, prepare_card_thumb


def _preview(url: str, title: str = "Title", *, thumb: bool = True) -> VideoPreview:
    data = None
    if thumb:
        img = Image.new("RGB", (320, 180), color=(10, 20, 30))
        import io

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        data = buf.getvalue()
    return VideoPreview(url=url, title=title, thumbnail_bytes=data)


def test_put_and_get():
    cache = PreviewCache(max_workers=0)
    cache.put(_preview("https://www.youtube.com/watch?v=abc12345678"))
    got = cache.get("https://www.youtube.com/watch?v=abc12345678")
    assert got is not None
    assert got.title == "Title"
    thumb = cache.get_card_thumb("https://www.youtube.com/watch?v=abc12345678")
    assert thumb is not None
    assert thumb.size == (128, 72)


def test_request_skips_cached():
    cache = PreviewCache(max_workers=0)
    cache.put(_preview("https://www.youtube.com/watch?v=ddddddddddd"))
    with patch.object(cache, "_work_queue") as mock_q:
        cache.request(["https://www.youtube.com/watch?v=ddddddddddd"])
        mock_q.put.assert_not_called()


def test_request_dedupes_pending():
    cache = PreviewCache(max_workers=0)
    with cache._lock:
        cache._pending.add("https://www.youtube.com/watch?v=eeeeeeeeeee")
    with patch.object(cache, "_work_queue") as mock_q:
        cache.request(
            [
                "https://www.youtube.com/watch?v=eeeeeeeeeee",
                "https://www.youtube.com/watch?v=eeeeeeeeeee",
            ]
        )
        mock_q.put.assert_not_called()


def test_prepare_card_thumb_none_without_bytes():
    assert prepare_card_thumb(VideoPreview(url="u", title="t", thumbnail_bytes=None)) is None


def test_on_updated_called_on_put():
    cache = PreviewCache(max_workers=0)
    seen: list[str] = []
    cache.on_updated(seen.append)
    cache.put(_preview("https://www.youtube.com/watch?v=fffffffffff"))
    assert seen == ["https://www.youtube.com/watch?v=fffffffffff"]
