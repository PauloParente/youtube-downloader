"""Left navigation sidebar."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.config import APP_TITLE, APP_VERSION
from youtube_downloader.ui_qt.theme import ACCENT, CARD_BORDER, SIDEBAR_WIDTH


class NavSidebar(QFrame):
    ITEMS = (
        ("download", "⬇", "Downloads"),
        ("queue", "☰", "Fila"),
        ("library", "▦", "Biblioteca"),
        ("history", "↺", "Histórico"),
        ("settings", "⚙", "Configurações"),
    )

    def __init__(
        self,
        on_select: Callable[[str], None],
        on_about: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self._on_select = on_select
        self._on_about = on_about
        self._active_id = "download"
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 16)
        layout.setSpacing(4)

        brand = QHBoxLayout()
        icon = QLabel("▶")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background-color: {ACCENT}; border-radius: 8px; font-weight: bold;"
        )
        brand.addWidget(icon)
        titles = QVBoxLayout()
        titles.addWidget(QLabel(f"<b>{APP_TITLE}</b>"))
        titles.addWidget(QLabel(f"v{APP_VERSION}"))
        titles.itemAt(1).widget().setProperty("class", "muted")
        brand.addLayout(titles)
        layout.addLayout(brand)
        layout.addSpacing(12)

        for view_id, icon_char, label in self.ITEMS:
            btn = QPushButton(f"{icon_char}   {label}")
            btn.setObjectName("nav")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, vid=view_id: self._select(vid))
            self._buttons[view_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {CARD_BORDER};")
        layout.addWidget(sep)
        about_btn = QPushButton("ℹ   Sobre")
        about_btn.setObjectName("nav")
        about_btn.clicked.connect(on_about)
        layout.addWidget(about_btn)

        self.set_active("download")

    def _select(self, view_id: str) -> None:
        self.set_active(view_id)
        self._on_select(view_id)

    def set_active(self, view_id: str) -> None:
        self._active_id = view_id
        for vid, btn in self._buttons.items():
            btn.setChecked(vid == view_id)
