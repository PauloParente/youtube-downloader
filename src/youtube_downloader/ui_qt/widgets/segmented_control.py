"""Two-option segmented control (e.g. Vídeo / Áudio)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QWidget):
    def __init__(
        self,
        labels: tuple[str, str],
        parent: QWidget | None = None,
        *,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segmentedControl")
        self.setAutoFillBackground(False)
        self._on_changed = on_changed
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._group = QButtonGroup(self)
        self._buttons: list[QPushButton] = []
        for i, text in enumerate(labels):
            btn = QPushButton(text)
            btn.setObjectName("segment")
            btn.setCheckable(True)
            self._group.addButton(btn, i)
            layout.addWidget(btn)
            self._buttons.append(btn)
        self._buttons[0].setChecked(True)
        self._group.idClicked.connect(self._on_id_clicked)

    def _on_id_clicked(self, _id: int) -> None:
        if self._on_changed is not None:
            self._on_changed()

    def current_index(self) -> int:
        return self._group.checkedId()

    def set_index(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)

    def setEnabled(self, enabled: bool) -> None:
        for btn in self._buttons:
            btn.setEnabled(enabled)
