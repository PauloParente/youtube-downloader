"""Política de avanço da fila após eventos terminais (espelha app._handle_event)."""

from youtube_downloader.core.models import EventType


def _should_advance_queue_after(event_type: EventType) -> bool:
    """Contrato documentado em docs/ux-downloads-queue.md."""
    return event_type in (EventType.DONE, EventType.CANCELLED)


def test_done_advances_queue() -> None:
    assert _should_advance_queue_after(EventType.DONE) is True


def test_cancelled_advances_queue() -> None:
    assert _should_advance_queue_after(EventType.CANCELLED) is True


def test_error_does_not_advance_queue() -> None:
    assert _should_advance_queue_after(EventType.ERROR) is False
