"""Hub — Biblioteca e Histórico em abas."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.history_view import HistoryView
from youtube_downloader.ui_qt.library_view import LibraryView
from youtube_downloader.ui_qt.widgets import PageHeader, apply_page_margins


class MediaHubView(QWidget):
    def __init__(
        self,
        library_view: LibraryView,
        history_view: HistoryView,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.library_view = library_view
        self.history_view = history_view

        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        layout.addWidget(
            PageHeader(
                "Os meus downloads",
                "Arquivos na pasta de destino e histórico de transferências.",
            )
        )

        tabs = QTabWidget()
        tabs.setObjectName("mediaHubTabs")
        tabs.addTab(library_view, "Biblioteca")
        tabs.addTab(history_view, "Histórico")
        layout.addWidget(tabs, stretch=1)

    def refresh_library(self) -> None:
        self.library_view.refresh()

    def set_history_entries(self, entries) -> None:
        self.history_view.set_entries(entries)
