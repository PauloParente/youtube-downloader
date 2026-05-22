"""Download format options — always visible below preview."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from youtube_downloader.config import QUALITY_COMBO_VALUES
from youtube_downloader.ui_qt.theme_tokens import SPACE_MD, SPACE_SM
from youtube_downloader.ui_qt.widgets.buttons import LinkButton
from youtube_downloader.ui_qt.widgets.common import field_label, secondary_label
from youtube_downloader.ui_qt.widgets.segmented_control import SegmentedControl


class DownloadOptionsBar(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_changed: Callable[[], None] | None = None,
        on_open_settings: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("downloadOptionsBar")
        self.setAutoFillBackground(False)
        self._on_changed = on_changed

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACE_SM)

        row = QHBoxLayout()
        row.setSpacing(SPACE_MD)

        self._format_segment = SegmentedControl(
            ("Vídeo", "Áudio"),
            parent=self,
            on_changed=self._emit_changed,
        )
        row.addWidget(self._format_segment)

        quality_col = QHBoxLayout()
        quality_col.setSpacing(SPACE_SM)
        quality_col.addWidget(field_label("Qualidade"))
        self._quality_combo = QComboBox()
        self._quality_combo.addItems(QUALITY_COMBO_VALUES)
        self._quality_combo.currentTextChanged.connect(
            lambda _: self._emit_changed()
        )
        quality_col.addWidget(self._quality_combo, stretch=1)
        row.addLayout(quality_col, stretch=1)
        root.addLayout(row)

        hint_row = QHBoxLayout()
        hint_row.addWidget(
            secondary_label(
                "Opções deste download — gravadas ao clicar em Baixar. "
                "Padrões globais em Configurações."
            )
        )
        if on_open_settings is not None:
            link = LinkButton("Abrir Configurações")
            link.clicked.connect(on_open_settings)
            hint_row.addWidget(link)
        root.addLayout(hint_row)

        self._on_audio_changed()

    @property
    def quality_combo(self) -> QComboBox:
        return self._quality_combo

    def is_audio_only(self) -> bool:
        return self._format_segment.current_index() == 1

    def set_audio_only(self, audio_only: bool) -> None:
        self._format_segment.set_index(1 if audio_only else 0)
        self._on_audio_changed()

    def _emit_changed(self) -> None:
        self._on_audio_changed()
        if self._on_changed is not None:
            self._on_changed()

    def _on_audio_changed(self) -> None:
        self._quality_combo.setEnabled(not self.is_audio_only())

    def set_enabled(self, enabled: bool) -> None:
        self._format_segment.setEnabled(enabled)
        self._quality_combo.setEnabled(enabled and not self.is_audio_only())
