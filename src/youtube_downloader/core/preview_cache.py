"""Centralized preview metadata cache with a small worker pool."""

from __future__ import annotations

import io
import queue
import threading
from collections.abc import Callable
from typing import Optional

from typing import TYPE_CHECKING

from youtube_downloader.core.logging_config import get_logger

if TYPE_CHECKING:
    from PIL import Image
from youtube_downloader.core.metadata import VideoPreview, fetch_preview, is_youtube_url

logger = get_logger(__name__)

CARD_THUMB_SIZE = (128, 72)
_DEFAULT_WORKERS = 3


def pil_rgb_from_bytes(data: bytes) -> Image.Image:
    from PIL import Image

    base = Image.open(io.BytesIO(data))
    if base.mode == "RGBA":
        background = Image.new("RGB", base.size, (40, 40, 40))
        background.paste(base, mask=base.split()[3])
        return background
    return base.convert("RGB")


def prepare_card_thumb(preview: VideoPreview) -> Optional[Image.Image]:
    from PIL import Image

    if not preview.thumbnail_bytes:
        return None
    try:
        img = pil_rgb_from_bytes(preview.thumbnail_bytes)
        return img.resize(CARD_THUMB_SIZE, Image.Resampling.LANCZOS)
    except Exception:
        logger.exception("Falha ao preparar miniatura do card")
        return None


class PreviewCache:
    """Thread-safe cache for VideoPreview and pre-resized queue card thumbnails."""

    def __init__(self, max_workers: int = _DEFAULT_WORKERS) -> None:
        self._cache: dict[str, VideoPreview] = {}
        self._card_thumbs: dict[str, Image.Image] = {}
        self._pending: set[str] = set()
        self._work_queue: queue.Queue[str | None] = queue.Queue()
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[str], None]] = []
        self._workers_started = False
        self._max_workers = max_workers

    def _ensure_workers(self) -> None:
        if self._workers_started or self._max_workers <= 0:
            return
        self._workers_started = True
        for _ in range(self._max_workers):
            threading.Thread(target=self._worker_loop, daemon=True).start()

    def _worker_loop(self) -> None:
        while True:
            url = self._work_queue.get()
            try:
                if url is None:
                    break
                self._fetch_and_store(url)
            finally:
                self._work_queue.task_done()

    def _fetch_and_store(self, url: str) -> None:
        try:
            meta = fetch_preview(url)
        except Exception:
            logger.exception("Falha ao obter metadados: %s", url[:80])
            meta = VideoPreview(
                url=url, title="", thumbnail_bytes=None, error="fetch failed"
            )

        with self._lock:
            self._pending.discard(url)
            if not meta.error:
                self._cache[url] = meta
                thumb = prepare_card_thumb(meta)
                if thumb is not None:
                    self._card_thumbs[url] = thumb

        for callback in self._snapshot_callbacks():
            try:
                callback(url)
            except Exception:
                logger.exception("PreviewCache callback falhou: %s", url[:80])

    def _snapshot_callbacks(self) -> list[Callable[[str], None]]:
        with self._lock:
            return list(self._callbacks)

    def get(self, url: str) -> Optional[VideoPreview]:
        with self._lock:
            return self._cache.get(url.strip())

    def get_card_thumb(self, url: str) -> Optional[Image.Image]:
        with self._lock:
            return self._card_thumbs.get(url.strip())

    def put(self, preview: VideoPreview) -> None:
        """Store preview (e.g. from Downloads URL field) without re-fetching."""
        url = preview.url.strip()
        if not url or preview.error:
            return
        notify = False
        with self._lock:
            self._cache[url] = preview
            thumb = prepare_card_thumb(preview)
            if thumb is not None:
                self._card_thumbs[url] = thumb
            notify = True
        if notify:
            for callback in self._snapshot_callbacks():
                try:
                    callback(url)
                except Exception:
                    logger.exception("PreviewCache callback falhou: %s", url[:80])

    def request(self, urls: list[str]) -> None:
        self._ensure_workers()
        for raw in urls:
            cleaned = raw.strip()
            if not cleaned or not is_youtube_url(cleaned):
                continue
            with self._lock:
                if cleaned in self._cache or cleaned in self._pending:
                    continue
                self._pending.add(cleaned)
            self._work_queue.put(cleaned)

    def on_updated(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def is_pending(self, url: str) -> bool:
        with self._lock:
            return url.strip() in self._pending
