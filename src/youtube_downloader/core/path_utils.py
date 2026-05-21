"""Cross-platform helpers for opening files and folders in the system shell."""

from __future__ import annotations

import os
import subprocess
import sys


def open_path_in_explorer(path: str) -> None:
    """Open a file or folder with the OS default handler."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)
