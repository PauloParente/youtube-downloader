"""Download format options — always visible below preview."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from youtube_downloader.config import QUALITY_COMBO_VALUES
from youtube_downloader.ui_qt.widgets.common import field_label
from youtube_downloader.ui_qt.widgets.segmented_control import SegmentedControl


class DownloadOptionsBar(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("downloadOptionsBar")
        self.setAutoFillBackground(False)
        self._on_changed = on_changed

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._format_segment = SegmentedControl(
            ("Vídeo", "Áudio"),
            parent=self,
            on_changed=self._emit_changed,
        )
        layout.addWidget(self._format_segment)

        quality_col = QHBoxLayout()
        quality_col.setSpacing(8)
        quality_col.addWidget(field_label("Qualidade"))
        self._quality_combo = QComboBox()
        self._quality_combo.addItems(QUALITY_COMBO_VALUES)
        self._quality_combo.currentTextChanged.connect(
            lambda _: self._emit_changed()
        )
        quality_col.addWidget(self._quality_combo, stretch=1)
        layout.addLayout(quality_col, stretch=1)

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
