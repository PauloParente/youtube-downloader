"""In-memory queue of YouTube URLs for sequential downloads."""

from dataclasses import dataclass, field


@dataclass
class DownloadQueue:
    """FIFO queue of video/playlist URLs."""

    _urls: list[str] = field(default_factory=list)

    def add(self, url: str) -> None:
        cleaned = url.strip()
        if cleaned and cleaned not in self._urls:
            self._urls.append(cleaned)

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
