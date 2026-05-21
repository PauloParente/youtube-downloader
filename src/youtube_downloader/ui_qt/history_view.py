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
from youtube_downloader.ui_qt.icons import icon_on_button, themed_icon
from youtube_downloader.ui_qt.util import pixmap_from_pil
from youtube_downloader.ui_qt.widgets import (
    CompactMediaRow,
    EmptyState,
    IconButton,
    LinkButton,
    PageHeader,
    apply_page_margins,
    muted_label,
    set_text_class,
)

HISTORY_THUMB_SIZE = (128, 72)
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
        apply_page_margins(layout)
        header = QHBoxLayout()
        header.addWidget(
            PageHeader("Histórico", "Downloads concluídos neste aplicativo."),
            stretch=1,
        )
        clear_btn = QPushButton("Limpar histórico")
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
        row = CompactMediaRow(thumb_size=HISTORY_THUMB_SIZE)
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
                row.set_pixmap(pixmap_from_pil(img, HISTORY_THUMB_SIZE))
            except OSError:
                row.set_placeholder("")
        else:
            row.set_placeholder("")

        yt_btn = IconButton(tooltip="Abrir no YouTube")
        icon_on_button(yt_btn, "play", size=18)
        yt_btn.setEnabled(
            bool(entry.source_url.strip() and is_youtube_url(entry.source_url))
        )
        yt_btn.clicked.connect(lambda: webbrowser.open(entry.source_url.strip()))
        row.actions_layout.addWidget(yt_btn)

        open_btn = IconButton(tooltip="Abrir arquivo")
        icon_on_button(open_btn, "file", size=18)
        open_btn.setEnabled(exists)
        open_btn.clicked.connect(lambda: self._on_open_file(path))
        row.actions_layout.addWidget(open_btn)

        folder_btn = IconButton(tooltip="Abrir pasta")
        icon_on_button(folder_btn, "folder", size=18)
        folder_btn.clicked.connect(lambda: self._on_open_folder(path))
        row.actions_layout.addWidget(folder_btn)

        redo_btn = IconButton(tooltip="Baixar de novo")
        icon_on_button(redo_btn, "download", size=18)
        redo_btn.setEnabled(bool(entry.source_url.strip()))
        redo_btn.clicked.connect(
            lambda: self._on_redownload(entry.source_url, entry.title)
        )
        row.actions_layout.addWidget(redo_btn)

        rem_btn = IconButton(tooltip="Remover do histórico")
        icon_on_button(rem_btn, "trash", size=18)
        rem_btn.clicked.connect(lambda: self._remove_entry(path))
        row.actions_layout.addWidget(rem_btn)

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
