"""Minimal bootstrap: logging, splash, then lazy MainWindow import."""

from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from youtube_downloader.config import (
    APP_TITLE,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_SIZE,
)
from youtube_downloader.core.logging_config import (
    get_logger,
    install_exception_hooks,
    setup_logging,
)
from youtube_downloader.core.settings import load_settings
from youtube_downloader.ui_qt.splash_screen import (
    SplashScreen,
    center_on_screen,
    parse_window_size,
)
from youtube_downloader.ui_qt.theme import apply_theme

if TYPE_CHECKING:
    from youtube_downloader.core.settings import AppSettings

logger = get_logger("startup")

_PROFILE_MARKS: list[tuple[str, float]] = []


def _profile_enabled() -> bool:
    return os.environ.get("YTD_STARTUP_PROFILE", "").strip() in ("1", "true", "yes")


def _profile_mark(name: str) -> None:
    if _profile_enabled():
        _PROFILE_MARKS.append((name, time.perf_counter()))


def _profile_log() -> None:
    if not _PROFILE_MARKS:
        return
    t0 = _PROFILE_MARKS[0][1]
    for name, t in _PROFILE_MARKS:
        logger.info("startup_profile %s=%.1fms", name, (t - t0) * 1000)


def run() -> None:
    """Start the Qt application (blocks in app.exec())."""
    _PROFILE_MARKS.clear()
    _profile_mark("run_start")

    setup_logging()
    install_exception_hooks()
    _profile_mark("logging_ready")
    logger.info("Aplicativo iniciado (PySide6)")

    app = QApplication.instance() or QApplication([])
    startup_settings = load_settings()
    apply_theme(app, startup_settings.appearance_mode)
    _profile_mark("qt_theme_ready")

    splash = SplashScreen(appearance_mode=startup_settings.appearance_mode)
    splash.show()
    app.processEvents()
    _profile_mark("splash_visible")

    from youtube_downloader.ui_qt.main_window import MainWindow

    window = MainWindow(
        settings=startup_settings,
        theme_already_applied=True,
    )
    _profile_mark("main_window_built")

    w, h = parse_window_size(WINDOW_SIZE)
    window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
    window.resize(w, h)
    window.setWindowTitle(APP_TITLE)
    center_on_screen(window)
    splash.finish(window)
    window.show()
    window.schedule_startup_tasks()
    _profile_mark("main_window_visible")
    _profile_log()

    if os.environ.get("YTD_MEASURE_STARTUP"):
        sys.exit(0)

    app.exec()
