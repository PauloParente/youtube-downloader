"""Library view — files in the downloads folder."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.core.library_scan import LibraryFile, scan_library_folder
from youtube_downloader.core.preview_cache import CARD_THUMB_SIZE
from youtube_downloader.ui_qt.icons import icon_on_button, themed_icon
from youtube_downloader.ui_qt.theme_tokens import ICON_LG, ICON_MD
from youtube_downloader.ui_qt.util import pixmap_from_pil
from youtube_downloader.ui_qt.widgets import (
    CompactMediaRow,
    EmptyState,
    GhostButton,
    muted_label,
)
from youtube_downloader.ui_qt.widgets.overflow_menu_button import OverflowMenuButton


class LibraryView(QWidget):
    def __init__(
        self,
        *,
        get_output_dir: Callable[[], str],
        on_open_path: Callable[[str], None],
        get_thumbnail_path: Callable[[str], Optional[str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_output_dir = get_output_dir
        self._on_open_path = on_open_path
        self._get_thumbnail_path = get_thumbnail_path
        self._files: list[LibraryFile] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.addStretch()
        refresh_btn = GhostButton("Atualizar")
        icon_on_button(refresh_btn, "library", size=ICON_MD)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        self._filter = QLineEdit()
        self._filter.setObjectName("filterInput")
        self._filter.setPlaceholderText("Filtrar arquivos...")
        self._filter.textChanged.connect(self._render_rows)
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

    def refresh(self) -> None:
        folder = self._get_output_dir().strip()
        self._files = scan_library_folder(folder)
        self._update_status(folder)
        self._render_rows()

    def _filtered(self) -> list[LibraryFile]:
        q = self._filter.text().strip().casefold()
        if not q:
            return self._files
        return [f for f in self._files if q in f.name.casefold()]

    def _update_status(self, folder: str) -> None:
        visible = self._filtered()
        total = len(self._files)
        q = self._filter.text().strip()
        if q and total:
            self._status.setText(f"{len(visible)} de {total} arquivo(s) em {folder}")
        elif total:
            self._status.setText(f"{total} arquivo(s) em {folder}")
        else:
            self._status.setText(f"Nenhum arquivo de mídia em {folder}")

    def _open_download_folder(self) -> None:
        folder = self._get_output_dir().strip()
        if folder:
            self._on_open_path(folder)

    def _render_rows(self) -> None:
        folder = self._get_output_dir().strip()
        self._update_status(folder)
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        visible = self._filtered()
        if not visible:
            if not self._files:
                empty = EmptyState(
                    "library",
                    "Pasta vazia",
                    "Nenhum arquivo de mídia na pasta de download.",
                    cta_label="Abrir pasta de download",
                    on_cta=self._open_download_folder,
                )
            else:
                empty = EmptyState(
                    "library",
                    "Nenhum resultado",
                    "Nenhum arquivo corresponde ao filtro.",
                )
            self._list_layout.addWidget(empty)
            return
        for item in visible:
            row = CompactMediaRow(thumb_size=CARD_THUMB_SIZE)
            row.set_title(item.name)
            row.set_meta(f"{item.format_ext} · {item.size_label}")
            thumb_path = (
                self._get_thumbnail_path(item.filepath)
                if self._get_thumbnail_path is not None
                else None
            )
            if thumb_path and os.path.isfile(thumb_path):
                try:
                    from PIL import Image

                    img = Image.open(thumb_path).convert("RGB")
                    row.set_pixmap(pixmap_from_pil(img, CARD_THUMB_SIZE))
                except OSError:
                    self._set_row_icon(row, item.is_audio)
            else:
                self._set_row_icon(row, item.is_audio)
            folder = os.path.dirname(item.filepath)
            menu = OverflowMenuButton()
            menu.set_actions(
                [
                    (
                        "Abrir arquivo",
                        lambda p=item.filepath: self._on_open_path(p),
                        True,
                    ),
                    (
                        "Abrir pasta",
                        lambda d=folder: self._on_open_path(d),
                        bool(folder),
                    ),
                ]
            )
            row.actions_layout.addWidget(menu)
            self._list_layout.addWidget(row)

    @staticmethod
    def _set_row_icon(row: CompactMediaRow, is_audio: bool) -> None:
        icon_name = "audio" if is_audio else "video"
        row.set_pixmap(themed_icon(icon_name, ICON_LG).pixmap(ICON_LG, ICON_LG))
