"""In-memory queue of YouTube URLs for sequential downloads."""

from dataclasses import dataclass, field


@dataclass
class DownloadQueue:
    """FIFO queue of video/playlist URLs."""

    _urls: list[str] = field(default_factory=list)

    def add(self, url: str) -> bool:
        """Append URL if non-empty and not already queued. Returns True if added."""
        cleaned = url.strip()
        if not cleaned or cleaned in self._urls:
            return False
        self._urls.append(cleaned)
        return True

    def remove_at(self, index: int) -> bool:
        """Remove pending item by index (0-based). Returns True if removed."""
        if index < 0 or index >= len(self._urls):
            return False
        del self._urls[index]
        return True

    def pop_next(self) -> str | None:
        if not self._urls:
            return None
        return self._urls.pop(0)

    def clear(self) -> None:
        self._urls.clear()

    def __len__(self) -> int:
        return len(self._urls)

    def snapshot(self) -> list[str]:
        return list(self._urls)
