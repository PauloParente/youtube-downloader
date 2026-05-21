"""Qt UI helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget

from youtube_downloader.core.preview_cache import pil_rgb_from_bytes


def schedule(widget: QWidget, delay_ms: int, callback: Callable[[], None]) -> None:
    """Run *callback* on the Qt main thread after *delay_ms*."""
    QTimer.singleShot(delay_ms, widget, callback)


def run_on_main(widget: QWidget, callback: Callable[[], None]) -> None:
    QTimer.singleShot(0, widget, callback)


def pixmap_from_pil(img, size: Optional[tuple[int, int]] = None) -> QPixmap:
    from PIL import Image

    if size:
        img = img.resize(size, Image.Resampling.LANCZOS)
    rgb = img.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


def pixmap_from_bytes(data: bytes, size: tuple[int, int]) -> Optional[QPixmap]:
    try:
        base = pil_rgb_from_bytes(data)
        return pixmap_from_pil(base, size)
    except Exception:
        return None
