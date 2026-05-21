"""Pure policy for queue UI sync and starting the next job after terminal events."""

from __future__ import annotations

from youtube_downloader.core.models import EventType


def should_sync_queue_structure(
    event_type: EventType,
    *,
    is_downloading: bool,
    queue_has_items: bool,
    continue_after_cancel: bool,
) -> bool:
    """Whether to refresh pending queue cards (mirrors app._handle_event)."""
    if event_type not in (
        EventType.DONE,
        EventType.CANCELLED,
        EventType.ERROR,
    ):
        return False
    if not is_downloading:
        return True
    if event_type == EventType.CANCELLED:
        return not continue_after_cancel
    if event_type == EventType.DONE:
        return not queue_has_items
    return True


def should_start_next_job(
    event_type: EventType,
    *,
    continue_after_cancel: bool,
) -> bool:
    """Whether the shell should pop and start the next queued URL."""
    if event_type == EventType.DONE:
        return True
    if event_type == EventType.CANCELLED and continue_after_cancel:
        return True
    return False


def is_terminal_download_event(event_type: EventType) -> bool:
    return event_type in (EventType.DONE, EventType.ERROR, EventType.CANCELLED)
