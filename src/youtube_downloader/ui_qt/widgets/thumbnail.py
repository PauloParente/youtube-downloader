"""Thumbnail with optional duration badge."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from youtube_downloader.ui_qt.theme_tokens import RADIUS_THUMB
from youtube_downloader.ui_qt.widgets.loading_spinner import LoadingSpinner


def _round_pixmap(pixmap: QPixmap, radius: int) -> QPixmap:
    """Clip pixmap to rounded rect (transparent corners)."""
    if pixmap.isNull() or radius <= 0:
        return pixmap
    out = QPixmap(pixmap.size())
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(out.rect()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return out


def _scale_cover(pixmap: QPixmap, width: int, height: int) -> QPixmap:
    scaled = pixmap.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - width) // 2)
    y = max(0, (scaled.height() - height) // 2)
    return scaled.copy(x, y, width, height)


class ThumbnailLabel(QWidget):
    def __init__(
        self,
        width: int,
        height: int,
        parent: QWidget | None = None,
        *,
        corner_radius: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("thumbSlot")
        self.setFixedSize(width, height)
        self._corner_radius = RADIUS_THUMB if corner_radius is None else corner_radius
        self._image = QLabel(self)
        self._image.setObjectName("thumb")
        self._image.setFixedSize(width, height)
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image.setAutoFillBackground(False)
        self._image.setContentsMargins(0, 0, 0, 0)
        self._spinner = LoadingSpinner(40, self)
        self._badge = QLabel(self)
        self._badge.setObjectName("durationBadge")
        self._badge.setAutoFillBackground(False)
        self._badge.hide()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self._image, 0, 0)
        grid.addWidget(
            self._spinner,
            0,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        grid.addWidget(
            self._badge,
            0,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )

    def set_loading(self, active: bool) -> None:
        if active:
            self._image.setPixmap(QPixmap())
            self._image.setText("")
            self._badge.hide()
            self._spinner.start()
        else:
            self._spinner.stop()

    def set_placeholder_text(self, text: str) -> None:
        self.set_loading(False)
        self._image.setPixmap(QPixmap())
        self._image.setText(text)
        self._badge.hide()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self.set_loading(False)
        self._image.setText("")
        if pixmap.isNull():
            self._image.setPixmap(pixmap)
            return
        w, h = self._image.width(), self._image.height()
        covered = _scale_cover(pixmap, w, h)
        self._image.setPixmap(_round_pixmap(covered, self._corner_radius))

    def set_duration_badge(self, text: str) -> None:
        if text:
            self._badge.setText(text)
            self._badge.show()
        else:
            self._badge.hide()
