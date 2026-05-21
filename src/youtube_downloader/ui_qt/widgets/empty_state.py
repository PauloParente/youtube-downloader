"""Centered empty state with icon and optional CTA."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.icons import themed_icon
from youtube_downloader.ui_qt.widgets.buttons import GhostButton
from youtube_downloader.ui_qt.widgets.common import secondary_label


class EmptyState(QWidget):
    def __init__(
        self,
        icon_name: str,
        title: str,
        subtitle: str = "",
        cta_label: str = "",
        on_cta: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 32, 24, 32)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setPixmap(themed_icon(icon_name, 40).pixmap(40, 40))
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setObjectName("sectionTitle")
        layout.addWidget(title_lbl)

        if subtitle:
            sub = secondary_label(subtitle)
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub.setWordWrap(True)
            layout.addWidget(sub)

        if cta_label and on_cta is not None:
            btn = GhostButton(cta_label)
            btn.clicked.connect(on_cta)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
