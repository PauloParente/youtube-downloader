"""Launcher from project root: python main.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from youtube_downloader.app import run

if __name__ == "__main__":
    run()
