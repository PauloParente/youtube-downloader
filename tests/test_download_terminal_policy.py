"""Backward-compatible imports for queue terminal policy tests."""

from youtube_downloader.core.models import EventType
from youtube_downloader.core.queue_coordinator import should_start_next_job

# Documented in docs/ux-downloads-queue.md — DONE/CANCELLED (skip) advance the queue.


def test_done_advances_queue() -> None:
    assert should_start_next_job(EventType.DONE, continue_after_cancel=False) is True


def test_cancelled_advances_queue_when_skip() -> None:
    assert should_start_next_job(EventType.CANCELLED, continue_after_cancel=True) is True


def test_error_does_not_advance_queue() -> None:
    assert should_start_next_job(EventType.ERROR, continue_after_cancel=False) is False
