"""Inline alert above preview on the Downloads screen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from youtube_downloader.ui_qt.icons import themed_icon
from youtube_downloader.ui_qt.icons import icon_on_button
from youtube_downloader.ui_qt.widgets.buttons import IconButton


class DownloadAlert(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("downloadAlert")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 8, 10)
        layout.setSpacing(10)

        self._icon = QLabel()
        self._icon.setPixmap(themed_icon("advanced", 18).pixmap(18, 18))
        self._icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._icon)

        self._message = QLabel()
        self._message.setWordWrap(True)
        layout.addWidget(self._message, stretch=1)

        close = IconButton(tooltip="Fechar")
        icon_on_button(close, "clear", size=14)
        close.clicked.connect(self.hide)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignTop)

    def show_alert(self, text: str) -> None:
        self._message.setText(text)
        self.show()

    def hide_alert(self) -> None:
        self.hide()
