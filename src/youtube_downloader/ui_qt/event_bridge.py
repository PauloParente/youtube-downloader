"""Thread-safe event bridge for download and preview progress."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from youtube_downloader.core.models import ProgressEvent


class EventBridge(QObject):
    """Emit ProgressEvent on the Qt main thread via queued signals."""

    progress = Signal(object)

    def emit_progress(self, event: ProgressEvent) -> None:
        self.progress.emit(event)
