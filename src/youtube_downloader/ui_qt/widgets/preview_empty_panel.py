"""Dashed preview placeholder (empty URL state)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.icons import icon_on_button, themed_icon
from youtube_downloader.ui_qt.theme_tokens import PREVIEW_EMPTY_MIN_HEIGHT
from youtube_downloader.ui_qt.widgets.buttons import LinkButton, SecondaryButton
from youtube_downloader.ui_qt.widgets.common import secondary_label


class PreviewEmptyPanel(QFrame):
    def __init__(
        self,
        icon_name: str,
        title: str,
        subtitle: str = "",
        *,
        on_paste: Callable[[], None] | None = None,
        on_open_queue: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("previewEmpty")
        self.setMinimumHeight(PREVIEW_EMPTY_MIN_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 32, 24, 32)

        icon_wrap = QFrame()
        icon_wrap.setObjectName("previewEmptyIcon")
        icon_layout = QVBoxLayout(icon_wrap)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setPixmap(
            themed_icon(icon_name, 24).pixmap(24, 24)
        )
        icon_layout.addWidget(icon_lbl)
        layout.addWidget(icon_wrap, alignment=Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setObjectName("sectionTitle")
        layout.addWidget(title_lbl)

        if subtitle:
            sub = secondary_label(subtitle)
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub.setWordWrap(True)
            layout.addWidget(sub)

        if on_paste is not None or on_open_queue is not None:
            actions = QHBoxLayout()
            actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
            actions.setSpacing(12)
            if on_paste is not None:
                paste_btn = SecondaryButton("Colar link")
                icon_on_button(paste_btn, "link", size=18)
                paste_btn.clicked.connect(on_paste)
                actions.addWidget(paste_btn)
            if on_open_queue is not None:
                self._queue_btn = LinkButton("Ver fila")
                self._queue_btn.clicked.connect(on_open_queue)
                actions.addWidget(self._queue_btn)
            else:
                self._queue_btn = None
            layout.addLayout(actions)

    def set_queue_link_text(self, text: str) -> None:
        if getattr(self, "_queue_btn", None) is not None:
            if text:
                self._queue_btn.setText(text)
                self._queue_btn.show()
            else:
                self._queue_btn.hide()
