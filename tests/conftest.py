"""Pytest hooks — headless Qt on Linux CI and servers."""

from __future__ import annotations

import os
import sys

# Must be set before any PySide6 import (collection imports ui_qt modules).
if sys.platform.startswith("linux") and "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
