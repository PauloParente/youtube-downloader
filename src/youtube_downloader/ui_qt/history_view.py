"""Download history view."""

from __future__ import annotations

import os
import webbrowser
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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
from youtube_downloader.ui_qt.util import pixmap_from_pil

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
        layout.setContentsMargins(24, 20, 24, 20)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(QLabel("<b style='font-size:22px'>Histórico</b>"))
        titles.addWidget(QLabel("Downloads concluídos neste aplicativo."))
        header.addLayout(titles)
        header.addStretch()
        clear_btn = QPushButton("Limpar histórico")
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtrar por título ou canal...")
        self._filter.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter)

        self._status = QLabel()
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
        self._on_filter_changed()

    def _on_filter_changed(self) -> None:
        self._update_status()
        try:
            self._render_rows()
        except Exception:
            logger.exception("Falha ao renderizar lista do historico")

    def _filtered(self) -> list[DownloadHistoryEntry]:
        q = self._filter.text().strip().casefold()
        if not q:
            return self._entries
        return [
            e
            for e in self._entries
            if q in e.title.casefold() or q in e.channel_name.casefold()
        ]

    def _update_status(self) -> None:
        total = len(self._entries)
        visible = self._filtered()
        q = self._filter.text().strip()
        if not total:
            self._status.setText("Nenhum download no histórico.")
            return
        text = f"{len(visible)} de {total} itens" if q else f"{total} itens no histórico"
        missing = sum(
            1
            for e in (visible if q else self._entries)
            if not os.path.isfile(e.filepath)
        )
        if missing:
            suffix = "arquivo" if missing == 1 else "arquivos"
            text += f" · {missing} {suffix} não encontrado(s) no disco"
        self._status.setText(text)

    def _render_rows(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        visible = self._filtered()
        if not visible:
            msg = (
                "Nenhum download no histórico. Conclua um download na tela Downloads."
                if not self._entries
                else "Nenhum resultado para este filtro."
            )
            self._list_layout.addWidget(QLabel(msg))
            return
        for entry in visible:
            self._list_layout.addWidget(self._make_card(entry))

    def _make_card(self, entry: DownloadHistoryEntry) -> QWidget:
        path = entry.filepath
        exists = os.path.isfile(path)
        card = QWidget()
        card.setObjectName("card")
        h = QHBoxLayout(card)

        thumb = QLabel()
        thumb.setFixedSize(*HISTORY_THUMB_SIZE)
        if entry.thumbnail_path and os.path.isfile(entry.thumbnail_path):
            try:
                from PIL import Image

                img = Image.open(entry.thumbnail_path).convert("RGB")
                thumb.setPixmap(pixmap_from_pil(img, HISTORY_THUMB_SIZE))
            except OSError:
                thumb.setText("▶" if not entry.is_audio else "♪")
        else:
            thumb.setText("▶" if not entry.is_audio else "♪")
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(thumb)

        body = QVBoxLayout()
        body.addWidget(QLabel(f"<b>{entry.title}</b>"))
        if entry.channel_name.strip():
            ch = QPushButton(entry.channel_name.strip())
            ch.setFlat(True)
            ch.setStyleSheet("color: #007BFF; text-align: left;")
            if entry.channel_url.strip():
                ch.clicked.connect(
                    lambda: webbrowser.open(entry.channel_url.strip())
                )
            body.addWidget(ch)
        size_label = format_file_size(entry.size_bytes) if exists else "—"
        body.addWidget(
            QLabel(
                f"{format_relative_date(entry.completed_at)} · "
                f"{entry.format_ext} · {size_label}"
            )
        )
        if not exists:
            body.addWidget(QLabel("Arquivo não encontrado"))
        h.addLayout(body, stretch=1)

        actions = QHBoxLayout()
        yt_btn = QPushButton("▶")
        yt_btn.setEnabled(bool(entry.source_url.strip() and is_youtube_url(entry.source_url)))
        yt_btn.clicked.connect(lambda: webbrowser.open(entry.source_url.strip()))
        actions.addWidget(yt_btn)
        open_btn = QPushButton("Abrir")
        open_btn.setEnabled(exists)
        open_btn.clicked.connect(lambda: self._on_open_file(path))
        actions.addWidget(open_btn)
        folder_btn = QPushButton("Pasta")
        folder_btn.clicked.connect(lambda: self._on_open_folder(path))
        actions.addWidget(folder_btn)
        redo_btn = QPushButton("Baixar de novo")
        redo_btn.setEnabled(bool(entry.source_url.strip()))
        redo_btn.clicked.connect(
            lambda: self._on_redownload(entry.source_url, entry.title)
        )
        actions.addWidget(redo_btn)
        rem_btn = QPushButton("Remover")
        rem_btn.clicked.connect(lambda: self._remove_entry(path))
        actions.addWidget(rem_btn)
        h.addLayout(actions)
        return card

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
