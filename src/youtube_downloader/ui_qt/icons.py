"""Load bundled SVG icons."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

_ICON_PKG = "youtube_downloader.resources.icons"


def _icons_dir() -> Path:
    try:
        ref = resources.files(_ICON_PKG)
        with resources.as_file(ref) as path:
            return path
    except (TypeError, FileNotFoundError):
        return Path(__file__).resolve().parent.parent / "resources" / "icons"


@lru_cache(maxsize=64)
def _svg_bytes(name: str) -> bytes:
    path = _icons_dir() / f"{name}.svg"
    if not path.is_file():
        raise FileNotFoundError(f"Icon not found: {path}")
    return path.read_bytes()


def themed_icon(name: str, size: int = 18, color: str | None = None) -> QIcon:
    """Render SVG icon; optional tint for light/dark."""
    data = _svg_bytes(name)
    if color is None:
        from youtube_downloader.ui_qt.theme import current_appearance_palette
        from youtube_downloader.ui_qt.theme_tokens import LIGHT

        color = "#5C5C5C" if current_appearance_palette() is LIGHT else "#A0A0A0"
    tinted = (
        data.replace(b"#888888", color.encode())
        .replace(b'fill="#888888"', f'fill="{color}"'.encode())
        .replace(b'stroke="#888888"', f'stroke="{color}"'.encode())
    )
    renderer = QSvgRenderer(tinted)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def accent_icon(name: str, size: int = 18) -> QIcon:
    from youtube_downloader.ui_qt.theme_tokens import ACCENT

    return themed_icon(name, size=size, color=ACCENT)


def icon_on_button(button, name: str, size: int = 18, accent: bool = False) -> None:
    ic = accent_icon(name, size) if accent else themed_icon(name, size)
    button.setIcon(ic)
    button.setIconSize(QSize(size, size))
