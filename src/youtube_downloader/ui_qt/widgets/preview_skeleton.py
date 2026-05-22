"""Skeleton placeholder for video preview (empty / loading)."""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, Qt, QTimer
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.animation_timing import pulse_opacity, repaint_interval_ms
from youtube_downloader.ui_qt.widgets.common import muted_label

_SHIMMER_PERIOD_MS = 1800
_SHIMMER_OPACITY_LOW = 0.35
_SHIMMER_OPACITY_HIGH = 0.65


def _skeleton_line(width: int, parent: QWidget) -> QFrame:
    line = QFrame(parent)
    line.setObjectName("skeletonLine")
    line.setFixedHeight(10)
    line.setFixedWidth(width)
    return line


class PreviewSkeleton(QFrame):
    THUMB_W = 240
    THUMB_H = 135

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("surfaceInset")
        self.setMinimumHeight(120)
        self._shimmer_lines: list[QFrame] = []
        self._shimmer_effects: list[QGraphicsOpacityEffect] = []
        self._shimmer_elapsed = QElapsedTimer()
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.setInterval(repaint_interval_ms())
        self._shimmer_timer.timeout.connect(self._tick_shimmer)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(16)
        thumb = QFrame()
        thumb.setObjectName("thumb")
        thumb.setFixedSize(self.THUMB_W, self.THUMB_H)
        row.addWidget(thumb)

        lines = QVBoxLayout()
        lines.setSpacing(8)
        for width in (200, 140, 100):
            line = _skeleton_line(width, self)
            self._shimmer_lines.append(line)
            lines.addWidget(line)
        lines.addStretch()
        row.addLayout(lines, stretch=1)
        root.addLayout(row)

        hint = muted_label("Cole um link do YouTube ou arraste para o campo acima")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)

    def start_shimmer(self) -> None:
        if not self._shimmer_lines:
            return
        if not self._shimmer_effects:
            for line in self._shimmer_lines:
                effect = QGraphicsOpacityEffect(line)
                line.setGraphicsEffect(effect)
                self._shimmer_effects.append(effect)
        if not self._shimmer_timer.isActive():
            self._shimmer_elapsed.start()
            self._shimmer_timer.start()

    def stop_shimmer(self) -> None:
        self._shimmer_timer.stop()
        for effect in self._shimmer_effects:
            effect.setOpacity(1.0)

    def _tick_shimmer(self) -> None:
        value = pulse_opacity(
            float(self._shimmer_elapsed.elapsed()),
            _SHIMMER_PERIOD_MS,
            _SHIMMER_OPACITY_LOW,
            _SHIMMER_OPACITY_HIGH,
        )
        for effect in self._shimmer_effects:
            effect.setOpacity(value)
