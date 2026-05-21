"""Small accent spinner for loading states."""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from youtube_downloader.ui_qt.theme_tokens import ACCENT

# Time-based rotation: smooth even when frames drop.
_REVOLUTION_MS = 1200
_REPAINT_INTERVAL_MS = 16  # ~60 Hz repaint cadence


class LoadingSpinner(QWidget):
    def __init__(self, size: int = 36, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(_REPAINT_INTERVAL_MS)
        self._timer.timeout.connect(self.update)
        self.hide()

    def start(self) -> None:
        self._elapsed.start()
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _current_angle(self) -> int:
        if not self._elapsed.isValid():
            return 0
        ms = self._elapsed.elapsed() % _REVOLUTION_MS
        return int((ms / _REVOLUTION_MS) * 360)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(ACCENT))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        margin = 4
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        start = -self._current_angle() * 16
        span = 270 * 16
        painter.drawArc(rect, start, span)
