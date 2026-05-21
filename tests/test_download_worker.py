"""Tests for QThread download worker lifecycle."""

from __future__ import annotations

from unittest.mock import MagicMock

from youtube_downloader.core.models import DownloadJob
from youtube_downloader.ui_qt.download_worker import DownloadWorker, start_download_thread


def test_start_download_thread_retains_worker_on_thread() -> None:
    downloader = MagicMock()
    job = DownloadJob(
        url="https://www.youtube.com/watch?v=test",
        output_dir="/tmp/out",
        quality="720p",
        audio_only=False,
    )
    thread = start_download_thread(downloader, job, on_progress=lambda _e: None, on_finished=lambda: None)
    try:
        assert hasattr(thread, "_download_worker")
        assert isinstance(thread._download_worker, DownloadWorker)
        assert thread._download_worker._job is job
    finally:
        thread.quit()
        thread.wait(2000)
