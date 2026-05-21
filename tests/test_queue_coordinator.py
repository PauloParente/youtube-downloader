"""Tests for core.queue_coordinator."""

from youtube_downloader.core.models import EventType
from youtube_downloader.core.queue_coordinator import (
    should_start_next_job,
    should_sync_queue_structure,
)


def test_sync_when_idle_on_done() -> None:
    assert (
        should_sync_queue_structure(
            EventType.DONE,
            is_downloading=False,
            queue_has_items=True,
            continue_after_cancel=False,
        )
        is True
    )


def test_no_sync_when_done_with_pending_while_downloading() -> None:
    assert (
        should_sync_queue_structure(
            EventType.DONE,
            is_downloading=True,
            queue_has_items=True,
            continue_after_cancel=False,
        )
        is False
    )


def test_sync_when_done_finishes_batch() -> None:
    assert (
        should_sync_queue_structure(
            EventType.DONE,
            is_downloading=True,
            queue_has_items=False,
            continue_after_cancel=False,
        )
        is True
    )


def test_sync_on_cancel_stop_all() -> None:
    assert (
        should_sync_queue_structure(
            EventType.CANCELLED,
            is_downloading=True,
            queue_has_items=True,
            continue_after_cancel=False,
        )
        is True
    )


def test_no_sync_on_cancel_skip() -> None:
    assert (
        should_sync_queue_structure(
            EventType.CANCELLED,
            is_downloading=True,
            queue_has_items=True,
            continue_after_cancel=True,
        )
        is False
    )


def test_sync_on_error_while_downloading() -> None:
    assert (
        should_sync_queue_structure(
            EventType.ERROR,
            is_downloading=True,
            queue_has_items=True,
            continue_after_cancel=False,
        )
        is True
    )


def test_start_next_on_done() -> None:
    assert should_start_next_job(EventType.DONE, continue_after_cancel=False) is True


def test_start_next_on_cancel_skip() -> None:
    assert should_start_next_job(EventType.CANCELLED, continue_after_cancel=True) is True


def test_no_start_next_on_cancel_stop() -> None:
    assert should_start_next_job(EventType.CANCELLED, continue_after_cancel=False) is False


def test_no_start_next_on_error() -> None:
    assert should_start_next_job(EventType.ERROR, continue_after_cancel=False) is False
