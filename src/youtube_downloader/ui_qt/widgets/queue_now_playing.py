"""Now-playing card on the Queue screen — layout aligned with the design system."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import VideoPreview
from youtube_downloader.core.preview_cache import CARD_THUMB_SIZE, pil_rgb_from_bytes
from youtube_downloader.ui_qt.icons import icon_on_button
from youtube_downloader.ui_qt.util import pixmap_from_bytes, pixmap_from_pil
from youtube_downloader.ui_qt.widgets.buttons import DangerButton, GhostButton, LinkButton
from youtube_downloader.ui_qt.widgets.card import Card
from youtube_downloader.ui_qt.widgets.common import muted_label, secondary_label
from youtube_downloader.ui_qt.widgets.section import SectionTitle
from youtube_downloader.ui_qt.widgets.thumbnail import ThumbnailLabel
from youtube_downloader.ui_qt.theme_tokens import SPACE_SM

logger = get_logger(__name__)

IDLE_TITLE = "Nenhum download em andamento"
DEFAULT_STATUS = "Aguardando…"


class QueueNowPlayingCard(Card):
    """
    Card *Baixando agora*: miniatura 128×72 (igual à fila pendente), metadados,
    barra de progresso em largura total e ações Cancelar / Pular.
    """

    def __init__(
        self,
        parent: QFrame | None = None,
        *,
        on_cancel: Callable[[], None],
        on_skip: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        body = self.body_layout
        body.addWidget(SectionTitle("Baixando agora"))

        inset = QFrame()
        inset.setObjectName("surfaceInset")
        inset_layout = QHBoxLayout(inset)
        inset_layout.setContentsMargins(SPACE_SM, SPACE_SM, SPACE_SM, SPACE_SM)
        inset_layout.setSpacing(12)
        inset_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._thumb = ThumbnailLabel(*CARD_THUMB_SIZE)
        inset_layout.addWidget(self._thumb, alignment=Qt.AlignmentFlag.AlignTop)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self._title = QLabel()
        self._title.setWordWrap(True)
        self._title.setObjectName("previewTitle")
        info_col.addWidget(self._title)

        self._meta = muted_label("")
        self._meta.setWordWrap(True)
        info_col.addWidget(self._meta)

        status_row = QHBoxLayout()
        status_row.setSpacing(SPACE_SM)
        self._status = muted_label(DEFAULT_STATUS)
        status_row.addWidget(self._status, stretch=1)
        self._percent = muted_label("0%")
        status_row.addWidget(self._percent)
        info_col.addLayout(status_row)
        info_col.addStretch()
        inset_layout.addLayout(info_col, stretch=1)
        body.addWidget(inset)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        body.addWidget(self._progress)

        self._idle_hint = secondary_label(
            "Inicie um download na tela Downloads ou use + Fila para enfileirar."
        )
        self._idle_hint.setWordWrap(True)
        self._idle_hint.hide()
        body.addWidget(self._idle_hint)

        self._idle_link: LinkButton | None = None

        actions = QHBoxLayout()
        actions.setSpacing(SPACE_SM)
        self.cancel_button = DangerButton("Cancelar")
        icon_on_button(self.cancel_button, "clear", size=16)
        self.cancel_button.clicked.connect(on_cancel)
        actions.addWidget(self.cancel_button)
        self.skip_button = QPushButton("Pular")
        icon_on_button(self.skip_button, "skip", size=18)
        self.skip_button.clicked.connect(on_skip)
        actions.addWidget(self.skip_button)
        actions.addStretch()
        body.addLayout(actions)

        self._active = False
        self._indeterminate = False
        self.set_idle()

    def configure_idle_actions(
        self, *, on_open_downloads: Callable[[], None] | None = None
    ) -> None:
        if on_open_downloads is None:
            return
        if self._idle_link is None:
            self._idle_link = LinkButton("Abrir Downloads")
            self._idle_link.clicked.connect(on_open_downloads)
            self.body_layout.addWidget(
                self._idle_link, alignment=Qt.AlignmentFlag.AlignLeft
            )
        self._idle_link.show()

    def set_idle(self) -> None:
        self._active = False
        self._indeterminate = False
        self._title.setText(IDLE_TITLE)
        self._meta.setText("")
        self._status.setText("")
        self._percent.setText("0%")
        self._thumb.set_placeholder_text("")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.hide()
        self._status.hide()
        self._percent.hide()
        self._idle_hint.show()
        if self._idle_link is not None:
            self._idle_link.show()
        self.cancel_button.setEnabled(False)
        self.skip_button.setEnabled(False)

    def set_active(
        self,
        *,
        title: str,
        meta: str,
        status: str = DEFAULT_STATUS,
        percent: Optional[float] = None,
    ) -> None:
        self._active = True
        self._idle_hint.hide()
        if self._idle_link is not None:
            self._idle_link.hide()
        self._title.setText(title.strip() or IDLE_TITLE)
        self._meta.setText(meta)
        self._status.setText(status or DEFAULT_STATUS)
        self._status.show()
        self._percent.show()
        self._progress.show()
        if percent is not None:
            self._set_determinate_percent(percent)
        else:
            self.set_indeterminate(True)

    def set_title(self, text: str) -> None:
        if text.strip():
            self._title.setText(text.strip())

    def set_status(self, text: str) -> None:
        if self._active:
            self._status.setText(text)

    def set_indeterminate(self, active: bool) -> None:
        if not self._active:
            return
        self._indeterminate = active
        if active:
            self._progress.setRange(0, 0)
            self._percent.setText("…")
        else:
            self._progress.setRange(0, 100)

    def _set_determinate_percent(self, percent: float) -> None:
        self._indeterminate = False
        self._progress.setRange(0, 100)
        value = max(0, min(100, int(percent * 100)))
        self._progress.setValue(value)
        self._percent.setText(f"{value}%")

    def set_percent(self, percent: Optional[float]) -> None:
        if not self._active:
            return
        if percent is None:
            self.set_indeterminate(True)
            return
        self._set_determinate_percent(percent)

    def set_meta_lines(self, url_line: str, hint: str = "") -> None:
        if not self._active:
            return
        lines: list[str] = []
        if url_line.strip():
            lines.append(url_line.strip())
        if hint.strip():
            lines.append(hint.strip())
        self._meta.setText("\n".join(lines))

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if not pixmap.isNull():
            self._thumb.set_pixmap(pixmap)

    def set_thumb_placeholder(self, text: str = "…") -> None:
        self._thumb.set_placeholder_text(text)

    def apply_thumbnail(
        self,
        url: str,
        *,
        get_card_thumb: Callable[[str], Optional[object]],
        get_cached_preview: Callable[[str], Optional[VideoPreview]],
        is_preview_pending: Callable[[str], bool],
    ) -> None:
        """Load thumbnail via PreviewCache (same rules as pending queue rows)."""
        cleaned = url.strip()
        if not cleaned:
            return
        pil_thumb = get_card_thumb(cleaned)
        if pil_thumb is not None:
            px = pixmap_from_pil(pil_thumb)
            if px is not None:
                self.set_pixmap(px)
                return
        preview = get_cached_preview(cleaned)
        if preview and preview.thumbnail_bytes:
            try:
                img = pil_rgb_from_bytes(preview.thumbnail_bytes)
                px = pixmap_from_pil(img)
                if px is not None:
                    self.set_pixmap(px)
                    return
            except Exception:
                logger.exception(
                    "Falha ao aplicar miniatura em Baixando agora: %s", cleaned[:80]
                )
        if is_preview_pending(cleaned):
            self.set_thumb_placeholder("…")

    def set_skip_enabled(self, enabled: bool, *, emphasize: bool = False) -> None:
        from youtube_downloader.ui_qt.theme import polish_widget

        self.skip_button.setEnabled(enabled and self._active)
        self.skip_button.setObjectName("primary" if emphasize and enabled else "")
        polish_widget(self.skip_button)

    def set_cancel_enabled(self, enabled: bool) -> None:
        self.cancel_button.setEnabled(enabled and self._active)
