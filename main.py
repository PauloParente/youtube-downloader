"""Launcher from project root: python main.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from youtube_downloader.app import run
from youtube_downloader.core.logging_config import install_exception_hooks, setup_logging

if __name__ == "__main__":
    setup_logging()
    install_exception_hooks()
    run()
