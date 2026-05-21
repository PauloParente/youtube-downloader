"""Library view — files in the downloads folder."""

from __future__ import annotations

from collections.abc import Callable

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
from youtube_downloader.ui_qt.icons import icon_on_button, themed_icon
from youtube_downloader.ui_qt.widgets import (
    CompactMediaRow,
    EmptyState,
    GhostButton,
    PageHeader,
    apply_page_margins,
    muted_label,
)


class LibraryView(QWidget):
    def __init__(
        self,
        *,
        get_output_dir: Callable[[], str],
        on_open_path: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_output_dir = get_output_dir
        self._on_open_path = on_open_path
        self._files: list[LibraryFile] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        header = QHBoxLayout()
        header.addWidget(
            PageHeader(
                "Biblioteca",
                "Arquivos de mídia na pasta de destino configurada.",
            ),
            stretch=1,
        )
        refresh_btn = GhostButton("Atualizar")
        icon_on_button(refresh_btn, "library", size=18)
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
            row = CompactMediaRow()
            row.set_title(item.name)
            row.set_meta(f"{item.format_ext} · {item.size_label}")
            icon_name = "audio" if item.is_audio else "video"
            row.set_pixmap(themed_icon(icon_name, 32).pixmap(32, 32))
            open_btn = QPushButton()
            open_btn.setObjectName("iconOnly")
            icon_on_button(open_btn, "folder", size=18)
            open_btn.setToolTip("Abrir arquivo")
            open_btn.clicked.connect(
                lambda checked, p=item.filepath: self._on_open_path(p)
            )
            row.actions_layout.addWidget(open_btn)
            self._list_layout.addWidget(row)
