"""Layout and label helpers."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLayout, QLabel, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.theme import polish_widget
from youtube_downloader.ui_qt.theme_tokens import PAGE_MARGINS, SPACE_LG


def apply_page_margins(layout: QVBoxLayout) -> None:
    l, t, r, b = PAGE_MARGINS
    layout.setContentsMargins(l, t, r, b)


def apply_layout_spacing(layout: QLayout, *, gap: int = SPACE_LG) -> None:
    """Apply consistent inter-widget spacing (8px grid)."""
    layout.setSpacing(gap)


def set_text_class(widget: QWidget, css_class: str) -> None:
    widget.setProperty("class", css_class)
    polish_widget(widget)


def muted_label(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    set_text_class(label, "muted")
    return label


def secondary_label(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    set_text_class(label, "secondary")
    return label


def field_label(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setAutoFillBackground(False)
    set_text_class(label, "fieldLabel")
    return label
