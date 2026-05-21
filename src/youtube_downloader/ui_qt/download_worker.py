"""Background download worker (QThread + signals)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal

from youtube_downloader.core.downloader import YoutubeDownloader
from youtube_downloader.core.models import DownloadJob, ProgressEvent


class DownloadWorker(QObject):
    """Runs YoutubeDownloader.download in a QThread."""

    finished = Signal()
    progress = Signal(object)

    def __init__(self, downloader: YoutubeDownloader, job: DownloadJob) -> None:
        super().__init__()
        self._downloader = downloader
        self._job = job

    def run(self) -> None:
        def on_event(event: ProgressEvent) -> None:
            self.progress.emit(event)

        try:
            self._downloader.download(self._job, on_event)
        finally:
            self.finished.emit()


def start_download_thread(
    downloader: YoutubeDownloader,
    job: DownloadJob,
    on_progress: Callable[[ProgressEvent], None],
    on_finished: Callable[[], None],
) -> QThread:
    """Start a download worker thread; returns the QThread (caller should keep reference)."""
    thread = QThread()
    worker = DownloadWorker(downloader, job)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.progress.connect(on_progress)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(on_finished)
    thread.start()
    return thread
