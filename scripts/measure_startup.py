"""Measure application startup phases (dev only; exits before event loop)."""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Headless Qt for scripted measurement
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _run_once() -> dict[str, float]:
    marks: list[tuple[str, float]] = []

    def mark(name: str) -> None:
        marks.append((name, time.perf_counter()))

    mark("start")

    from youtube_downloader.core.logging_config import install_exception_hooks, setup_logging

    setup_logging()
    install_exception_hooks()
    mark("logging_ready")

    from PySide6.QtWidgets import QApplication

    from youtube_downloader.core.settings import load_settings
    from youtube_downloader.ui_qt.splash_screen import SplashScreen
    from youtube_downloader.ui_qt.theme import apply_theme

    app = QApplication.instance() or QApplication([])
    settings = load_settings()
    apply_theme(app, settings.appearance_mode)
    mark("qt_theme_ready")

    splash = SplashScreen(appearance_mode=settings.appearance_mode)
    splash.show()
    app.processEvents()
    mark("splash_visible")

    from youtube_downloader.ui_qt.main_window import MainWindow

    window = MainWindow(
        settings=settings,
        theme_already_applied=True,
    )
    mark("main_window_built")

    window.show()
    app.processEvents()
    mark("main_window_visible")

    t0 = marks[0][1]
    return {name: (t - t0) * 1000 for name, t in marks}


def _print_table(all_runs: list[dict[str, float]]) -> None:
    keys = list(all_runs[0].keys())
    print(f"{'phase':<22}  {'ms':>8}  (median of {len(all_runs)} runs)")
    print("-" * 40)
    for key in keys:
        values = [r[key] for r in all_runs]
        med = statistics.median(values)
        print(f"{key:<22}  {med:8.1f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure YouTube Downloader startup")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs (default: 5)")
    args = parser.parse_args()
    runs = max(1, args.runs)
    results = [_run_once() for _ in range(runs)]
    _print_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
