"""Entry point: python -m youtube_downloader"""

import sys
from pathlib import Path

# Allow running from project root without installing the package
_src = Path(__file__).resolve().parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from youtube_downloader.app import run

if __name__ == "__main__":
    run()
