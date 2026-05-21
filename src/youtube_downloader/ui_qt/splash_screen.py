"""Splash screen during startup."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QSplashScreen, QVBoxLayout, QWidget

from youtube_downloader.config import APP_TITLE, APP_VERSION, SPLASH_LOGO_PATH, SPLASH_SIZE
from youtube_downloader.ui_qt.theme_tokens import ACCENT_MUTED, DARK, FONT_CAPTION, FONT_PAGE_TITLE
from youtube_downloader.ui_qt.widgets import secondary_label


def parse_window_size(size: str) -> tuple[int, int]:
    parts = size.lower().split("x", 1)
    return int(parts[0]), int(parts[1])


def center_on_screen(widget: QWidget) -> None:
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    x = geo.x() + (geo.width() - widget.width()) // 2
    y = geo.y() + (geo.height() - widget.height()) // 2
    widget.move(x, y)


def _splash_stylesheet() -> str:
    p = DARK
    return f"""
        QWidget {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {p.app_bg},
                stop:0.5 {p.card_bg},
                stop:1 {ACCENT_MUTED}
            );
        }}
        QLabel {{
            background: transparent;
        }}
        QLabel#pageTitle {{
            font-size: {FONT_PAGE_TITLE}px;
            font-weight: 600;
            color: {p.text_primary};
        }}
        QLabel[class="secondary"] {{
            color: {p.text_secondary};
            font-size: {FONT_CAPTION}px;
        }}
    """


def _build_splash_pixmap(width: int, height: int) -> QPixmap:
    """Render splash content into a pixmap (QSplashScreen only paints pixmaps)."""
    content = QWidget()
    content.setFixedSize(width, height)
    content.setStyleSheet(_splash_stylesheet())

    layout = QVBoxLayout(content)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if SPLASH_LOGO_PATH.is_file():
        try:
            logo = QPixmap(str(SPLASH_LOGO_PATH)).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio
            )
            logo_lbl = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
            logo_lbl.setPixmap(logo)
            layout.addWidget(logo_lbl)
        except Exception:
            pass
    title = QLabel(f"<b>{APP_TITLE}</b> v{APP_VERSION}")
    title.setObjectName("pageTitle")
    layout.addWidget(title)
    layout.addWidget(secondary_label("A carregar. Por favor, aguarde…"))

    pixmap = QPixmap(width, height)
    content.render(pixmap)
    return pixmap


class SplashScreen:
    """Frameless splash shown while the main window loads."""

    def __init__(self) -> None:
        self._width, self._height = parse_window_size(SPLASH_SIZE)
        self._splash: QSplashScreen | None = None

    def show(self) -> None:
        pixmap = _build_splash_pixmap(self._width, self._height)
        self._splash = QSplashScreen(pixmap)
        self._splash.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )

        self._splash.show()
        center_on_screen(self._splash)

    def finish(self, main_window: QWidget) -> None:
        if self._splash is not None:
            self._splash.finish(main_window)
            self._splash = None

    def close(self) -> None:
        if self._splash is not None:
            self._splash.close()
            self._splash = None
