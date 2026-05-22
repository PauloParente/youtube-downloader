"""Download history view."""

from __future__ import annotations

import os
import webbrowser
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    format_file_size,
    format_relative_date,
)
from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import is_youtube_url
from youtube_downloader.core.preview_cache import CARD_THUMB_SIZE
from youtube_downloader.ui_qt.util import pixmap_from_pil
from youtube_downloader.ui_qt.widgets.overflow_menu_button import OverflowMenuButton
from youtube_downloader.ui_qt.widgets import (
    CompactMediaRow,
    DangerButton,
    EmptyState,
    muted_label,
)

logger = get_logger(__name__)


class HistoryView(QWidget):
    def __init__(
        self,
        *,
        on_open_folder: Callable[[str], None],
        on_open_file: Callable[[str], None],
        on_redownload: Callable[[str, str], None],
        on_remove: Callable[[str], list[DownloadHistoryEntry]],
        on_clear_history: Callable[[], list[DownloadHistoryEntry]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_open_folder = on_open_folder
        self._on_open_file = on_open_file
        self._on_redownload = on_redownload
        self._on_remove = on_remove
        self._on_clear_history = on_clear_history
        self._entries: list[DownloadHistoryEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.addStretch()
        clear_btn = DangerButton("Limpar histórico")
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        self._filter = QLineEdit()
        self._filter.setObjectName("filterInput")
        self._filter.setPlaceholderText("Filtrar por título ou canal...")
        self._filter.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter)

        self._status = muted_label("")
        layout.addWidget(self._status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._list_host = QWidget()
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._list_host)
        layout.addWidget(scroll, stretch=1)

    def set_entries(self, entries: list[DownloadHistoryEntry]) -> None:
        self._entries = list(entries)
        self._render_list()

    def _on_filter_changed(self) -> None:
        self._render_list()

    def _filtered_entries(self) -> list[DownloadHistoryEntry]:
        q = self._filter.text().strip().casefold()
        if not q:
            return self._entries
        return [
            e
            for e in self._entries
            if q in e.title.casefold()
            or q in (e.channel_name or "").casefold()
        ]

    def _render_list(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        visible = self._filtered_entries()
        self._status.setText(
            f"{len(visible)} de {len(self._entries)} item(ns)"
            if self._filter.text().strip() and self._entries
            else f"{len(self._entries)} item(ns) no histórico"
            if self._entries
            else "Nenhum download no histórico ainda."
        )
        if not visible:
            empty = EmptyState(
                "history",
                "Nenhum resultado." if self._entries else "Histórico vazio",
                "Ajuste o filtro."
                if self._entries
                else "Baixe um vídeo na tela Downloads para ver o histórico aqui.",
            )
            self._list_layout.addWidget(empty)
            return
        for entry in visible:
            self._list_layout.addWidget(self._make_card(entry))

    def _make_card(self, entry: DownloadHistoryEntry) -> QWidget:
        path = entry.filepath
        exists = os.path.isfile(path)
        row = CompactMediaRow(thumb_size=CARD_THUMB_SIZE)
        row.set_title(entry.title)
        size_label = format_file_size(entry.size_bytes) if exists else "—"
        channel = entry.channel_name.strip() or "—"
        row.set_meta(
            f"{channel} · {format_relative_date(entry.completed_at)} · "
            f"{entry.format_ext} · {size_label}"
        )
        if entry.thumbnail_path and os.path.isfile(entry.thumbnail_path):
            try:
                from PIL import Image

                img = Image.open(entry.thumbnail_path).convert("RGB")
                row.set_pixmap(pixmap_from_pil(img, CARD_THUMB_SIZE))
            except OSError:
                row.set_placeholder("")
        else:
            row.set_placeholder("")

        source = entry.source_url.strip()
        menu = OverflowMenuButton()
        menu.set_actions(
            [
                (
                    "Abrir arquivo",
                    lambda p=path: self._on_open_file(p),
                    exists,
                ),
                (
                    "Abrir pasta",
                    lambda p=path: self._on_open_folder(p),
                    True,
                ),
                (
                    "Abrir no YouTube",
                    lambda u=source: webbrowser.open(u),
                    bool(source and is_youtube_url(source)),
                ),
                (
                    "Baixar de novo",
                    lambda u=source, t=entry.title: self._on_redownload(u, t),
                    bool(source),
                ),
                (
                    "Remover do histórico",
                    lambda p=path: self._remove_entry(p),
                    True,
                ),
            ]
        )
        row.actions_layout.addWidget(menu)

        return row

    def _remove_entry(self, filepath: str) -> None:
        reply = QMessageBox.question(
            self,
            "Remover do histórico",
            "Remover este item do histórico?\nO arquivo no disco não será apagado.",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.set_entries(self._on_remove(filepath))

    def _clear_all(self) -> None:
        if not self._entries:
            return
        reply = QMessageBox.question(
            self,
            "Limpar histórico",
            "Limpar todo o histórico?\nOs arquivos no disco não serão apagados.",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.set_entries(self._on_clear_history())
