"""Splash screen during startup."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QSplashScreen, QVBoxLayout, QWidget

from youtube_downloader.config import APP_TITLE, APP_VERSION, SPLASH_LOGO_PATH, SPLASH_SIZE
from youtube_downloader.ui_qt.theme_tokens import DARK
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


class SplashScreen:
    """Frameless splash shown while the main window loads."""

    def __init__(self) -> None:
        self._width, self._height = parse_window_size(SPLASH_SIZE)
        self._splash: QSplashScreen | None = None

    def show(self) -> None:
        pixmap = QPixmap(self._width, self._height)
        pixmap.fill(DARK.app_bg)
        self._splash = QSplashScreen(pixmap)
        self._splash.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )

        content = QWidget()
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
        content.setFixedSize(self._width, self._height)
        content.setStyleSheet(f"background-color: {DARK.app_bg};")

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
