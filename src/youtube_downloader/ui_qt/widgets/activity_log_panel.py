"""Collapsible activity log (Queue screen, left column)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui_qt.icons import icon_on_button
from youtube_downloader.ui_qt.theme import polish_widget
from youtube_downloader.ui_qt.widgets.buttons import GhostButton
from youtube_downloader.ui_qt.widgets.card import Card
from youtube_downloader.ui_qt.widgets.common import muted_label
from youtube_downloader.ui_qt.widgets.section import SectionTitle

LOG_TEXTBOX_HEIGHT = 160
_LAST_LINE_TRUNCATE = 120


class _ActivityHeader(QWidget):
    """Header row; click empty/title area toggles expand (buttons keep their action)."""

    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        pos = event.position().toPoint()
        widget = self.childAt(pos)
        while widget is not None and widget is not self:
            if isinstance(widget, QPushButton):
                super().mousePressEvent(event)
                return
            widget = widget.parentWidget()
        self.clicked.emit()
        event.accept()


class ActivityLogPanel(Card):
    """Activity log: collapsed shows last line; expanded shows full log."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_expanded_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_expanded_changed = on_expanded_changed
        self._expanded = True
        self._lines_since_expand = 0
        self._last_message = ""
        self._clear_enabled = True

        card_layout = self.body_layout

        self._header = _ActivityHeader()
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row = QHBoxLayout(self._header)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setObjectName("sectionToggle")
        self._toggle_btn.clicked.connect(self._toggle_expanded)
        header_row.addWidget(self._toggle_btn)

        header_row.addWidget(SectionTitle("Atividade"))

        self._badge = QLabel("0")
        self._badge.setObjectName("durationBadge")
        self._badge.hide()
        header_row.addWidget(self._badge)

        header_row.addStretch()

        self._clear_btn = GhostButton("Limpar")
        self._clear_btn.clicked.connect(self.clear)
        header_row.addWidget(self._clear_btn)

        self._header.clicked.connect(self._toggle_expanded)
        card_layout.addWidget(self._header)

        self._last_line = muted_label("")
        self._last_line.setObjectName("activityLastLine")
        self._last_line.setWordWrap(True)
        self._last_line.hide()
        card_layout.addWidget(self._last_line)

        self._log_body = QWidget()
        log_inner = QVBoxLayout(self._log_body)
        log_inner.setContentsMargins(0, 0, 0, 0)
        self._log_box = QPlainTextEdit()
        self._log_box.setObjectName("logInset")
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(LOG_TEXTBOX_HEIGHT)
        log_inner.addWidget(self._log_box)
        card_layout.addWidget(self._log_body)

        self._sync_visibility()

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            self._sync_visibility()
            return
        self._expanded = expanded
        if expanded:
            self._lines_since_expand = 0
            self._update_badge()
        self._sync_visibility()
        self._notify_expanded_changed()

    def append(self, message: str) -> None:
        text = (message or "").strip()
        if not text:
            return
        self._last_message = text
        self._log_box.appendPlainText(text)
        self._log_box.verticalScrollBar().setValue(
            self._log_box.verticalScrollBar().maximum()
        )
        self._update_last_line()
        self._sync_clear_enabled()
        if not self._expanded:
            self._lines_since_expand += 1
            self._update_badge()

    def clear(self) -> None:
        self._log_box.clear()
        self._last_message = ""
        self._last_line.hide()
        self._lines_since_expand = 0
        self._update_badge()
        self._sync_clear_enabled()

    def set_clear_enabled(self, enabled: bool) -> None:
        self._clear_enabled = enabled
        self._sync_clear_enabled()

    def _toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded)

    def _notify_expanded_changed(self) -> None:
        if self._on_expanded_changed is not None:
            self._on_expanded_changed()

    def _update_last_line(self) -> None:
        if not self._last_message:
            self._last_line.hide()
            return
        preview = truncate_text(self._last_message, _LAST_LINE_TRUNCATE)
        self._last_line.setText(f"Última: {preview}")

    def _update_badge(self) -> None:
        if self._expanded or self._lines_since_expand <= 0:
            self._badge.hide()
        else:
            self._badge.setText(str(self._lines_since_expand))
            self._badge.show()

    def _sync_clear_enabled(self) -> None:
        has_text = bool(self._log_box.toPlainText().strip())
        self._clear_btn.setEnabled(self._clear_enabled and has_text)

    def _sync_visibility(self) -> None:
        self._toggle_btn.setProperty("expanded", "true" if self._expanded else "false")
        polish_widget(self._toggle_btn)
        icon_on_button(self._toggle_btn, "chevron", size=14)

        if self._expanded:
            self._log_body.show()
            self._log_box.setFixedHeight(LOG_TEXTBOX_HEIGHT)
            self._last_line.hide()
        else:
            self._log_body.hide()
            if self._last_message:
                self._update_last_line()
                self._last_line.show()
            else:
                self._last_line.hide()

        self._update_badge()
        self._sync_clear_enabled()
