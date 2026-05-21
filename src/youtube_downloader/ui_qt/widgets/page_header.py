"""Page title and subtitle."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.widgets.common import secondary_label


class PageHeader(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("pageTitle")
        layout.addWidget(title_lbl)
        self.subtitle_label: QLabel | None = None
        if subtitle:
            self.subtitle_label = secondary_label(subtitle)
            layout.addWidget(self.subtitle_label)

    def set_subtitle(self, text: str) -> None:
        if self.subtitle_label is not None:
            self.subtitle_label.setText(text)
