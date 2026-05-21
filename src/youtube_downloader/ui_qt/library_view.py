"""Library view — files in the downloads folder."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.core.library_scan import LibraryFile, scan_library_folder


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
        layout.setContentsMargins(24, 20, 24, 20)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(QLabel("<b style='font-size:22px'>Biblioteca</b>"))
        titles.addWidget(QLabel("Arquivos de mídia na pasta de destino configurada."))
        header.addLayout(titles)
        header.addStretch()
        refresh_btn = QPushButton("Atualizar")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtrar arquivos...")
        self._filter.textChanged.connect(self._render_rows)
        layout.addWidget(self._filter)

        self._status = QLabel()
        self._status.setProperty("class", "muted")
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

    def _render_rows(self) -> None:
        folder = self._get_output_dir().strip()
        self._update_status(folder)
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        visible = self._filtered()
        if not visible:
            msg = (
                "Nenhum arquivo encontrado. Baixe vídeos na tela Downloads."
                if not self._files
                else "Nenhum resultado para este filtro."
            )
            self._list_layout.addWidget(QLabel(msg))
            return
        for item in visible:
            row = QWidget()
            row.setObjectName("card")
            h = QHBoxLayout(row)
            icon = "♪" if item.is_audio else "▶"
            h.addWidget(QLabel(icon))
            col = QVBoxLayout()
            col.addWidget(QLabel(f"<b>{item.name}</b>"))
            col.addWidget(QLabel(f"{item.format_ext} · {item.size_label}"))
            h.addLayout(col, stretch=1)
            open_btn = QPushButton("Abrir")
            open_btn.clicked.connect(lambda checked, p=item.filepath: self._on_open_path(p))
            h.addWidget(open_btn)
            self._list_layout.addWidget(row)
