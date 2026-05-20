"""Fila de downloads — download atual e pendentes em cards."""

from __future__ import annotations

import io
from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

import customtkinter as ctk
from PIL import Image

from youtube_downloader.core.logging_config import get_logger
from youtube_downloader.core.metadata import VideoPreview, format_duration
from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.preview_cache import CARD_THUMB_SIZE, pil_rgb_from_bytes
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui.theme import (
    ACCENT,
    BTN_DISABLED,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    CARD_BORDER,
    CARD_STYLE,
    SECONDARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

logger = get_logger(__name__)

THUMB_DISPLAY_SIZE = (240, 135)
QUEUE_URL_TRUNCATE = 58
PENDING_SCROLL_HEIGHT = 400
STRUCTURE_DEBOUNCE_MS = 150
IDLE_NOW_PLAYING = "Nenhum download em andamento"
DEFAULT_NOW_STATUS = "Aguardando…"
LOADING_TITLE = "Carregando…"


@dataclass
class _PendingCardUi:
    frame: ctk.CTkFrame
    title_label: ctk.CTkLabel
    meta_label: ctk.CTkLabel
    thumb_col: ctk.CTkFrame
    index: int


class QueueView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        get_queue_snapshot: Callable[[], list[str]],
        get_cached_preview: Callable[[str], Optional[VideoPreview]],
        get_card_thumb: Callable[[str], Optional[Image.Image]],
        is_preview_pending: Callable[[str], bool],
        on_remove_queue_at: Callable[[int], None],
        on_cancel_download: Callable[[], None],
        on_skip_download: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._get_queue_snapshot = get_queue_snapshot
        self._get_cached_preview = get_cached_preview
        self._get_card_thumb = get_card_thumb
        self._is_preview_pending = is_preview_pending
        self._on_remove_queue_at = on_remove_queue_at
        self._on_cancel_download = on_cancel_download
        self._on_skip_download = on_skip_download

        self._is_downloading = False
        self._pending_scroll: Optional[ctk.CTkScrollableFrame] = None
        self._empty_label: Optional[ctk.CTkLabel] = None
        self._ctk_thumb_image: Optional[ctk.CTkImage] = None
        self._thumb_pil_light: Optional[Image.Image] = None
        self._thumb_pil_dark: Optional[Image.Image] = None
        self._placeholder_image: Optional[ctk.CTkImage] = None
        self._cards_by_url: dict[str, _PendingCardUi] = {}
        self._card_thumb_images: list[ctk.CTkImage] = []
        self._structure_refresh_after_id: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()

    def _build_ui(self) -> None:
        pad = 24

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=pad, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Fila",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self._subtitle_label = ctk.CTkLabel(
            header,
            text="Acompanhe o download atual e os próximos da fila.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self._subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self._now_card = ctk.CTkFrame(self, **CARD_STYLE)
        self._now_card.grid(row=1, column=0, padx=pad, pady=(0, 12), sticky="ew")
        self._now_card.grid_columnconfigure(0, weight=1)
        self._build_now_playing_card()

        self._pending_card = ctk.CTkFrame(self, **CARD_STYLE)
        self._pending_card.grid(row=2, column=0, padx=pad, pady=(0, 20), sticky="nsew")
        self._pending_card.grid_columnconfigure(0, weight=1)
        self._pending_card.grid_rowconfigure(1, weight=1)
        self._build_pending_card()

        self.refresh_structure()

    def _build_now_playing_card(self) -> None:
        inner = ctk.CTkFrame(self._now_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=14)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            inner,
            text="Baixando agora",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self._now_thumb_label = ctk.CTkLabel(
            inner,
            text="",
            width=THUMB_DISPLAY_SIZE[0],
            height=THUMB_DISPLAY_SIZE[1],
            fg_color=("#2a2a2a", "#2a2a2a"),
            corner_radius=6,
        )
        self._now_thumb_label.grid(row=1, column=0, rowspan=3, padx=(0, 12), sticky="nw")

        self._now_title_label = ctk.CTkLabel(
            inner,
            text=IDLE_NOW_PLAYING,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self._now_title_label.grid(row=1, column=1, sticky="ew")

        self._now_url_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self._now_url_label.grid(row=2, column=1, sticky="ew", pady=(4, 8))

        status_row = ctk.CTkFrame(inner, fg_color="transparent")
        status_row.grid(row=3, column=1, sticky="ew")
        status_row.grid_columnconfigure(0, weight=1)

        self._now_status_label = ctk.CTkLabel(
            status_row,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self._now_status_label.grid(row=0, column=0, sticky="w")

        self._now_pct_label = ctk.CTkLabel(
            status_row,
            text="0%",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="e",
        )
        self._now_pct_label.grid(row=0, column=1, sticky="e")

        self._now_progress_bar = ctk.CTkProgressBar(
            inner,
            height=6,
            progress_color=ACCENT,
            fg_color=("#2a2a2a", "#2a2a2a"),
        )
        self._now_progress_bar.set(0)
        self._now_progress_bar.grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(8, 12)
        )

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.grid(row=5, column=0, columnspan=2, sticky="ew")
        actions.grid_columnconfigure(2, weight=1)

        self._cancel_btn = ctk.CTkButton(
            actions,
            text="✕  Cancelar",
            width=120,
            height=36,
            command=self._on_cancel_download,
            state="disabled",
            fg_color=BTN_DISABLED,
            hover_color=BTN_SECONDARY,
            text_color=TEXT_PRIMARY,
            corner_radius=6,
        )
        self._cancel_btn.grid(row=0, column=0, padx=(0, 8))

        self._skip_btn = ctk.CTkButton(
            actions,
            text="⏭  Pular",
            width=100,
            height=36,
            command=self._on_skip_download,
            state="disabled",
            fg_color=BTN_DISABLED,
            hover_color=BTN_SECONDARY,
            text_color=TEXT_PRIMARY,
            corner_radius=6,
        )
        self._skip_btn.grid(row=0, column=1, padx=(0, 8))

        self._configure_now_thumb(None)

    def _build_pending_card(self) -> None:
        header = ctk.CTkFrame(self._pending_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)

        self._pending_title_label = ctk.CTkLabel(
            header,
            text="Na fila",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self._pending_title_label.grid(row=0, column=0, sticky="w")

        self._pending_scroll = ctk.CTkScrollableFrame(
            self._pending_card,
            height=PENDING_SCROLL_HEIGHT,
            fg_color=("gray18", "gray14"),
            corner_radius=6,
        )
        self._pending_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._pending_scroll.grid_columnconfigure(0, weight=1)

    def _ensure_placeholder_image(self) -> ctk.CTkImage:
        if self._placeholder_image is not None:
            return self._placeholder_image
        gray = Image.new("RGB", THUMB_DISPLAY_SIZE, (64, 64, 64))
        self._thumb_pil_light = gray.copy()
        self._thumb_pil_dark = gray.copy()
        self._placeholder_image = ctk.CTkImage(
            light_image=self._thumb_pil_light,
            dark_image=self._thumb_pil_dark,
            size=THUMB_DISPLAY_SIZE,
        )
        return self._placeholder_image

    def _configure_now_thumb(self, image: Optional[ctk.CTkImage]) -> None:
        self._now_thumb_label.configure(
            image=image if image is not None else self._ensure_placeholder_image(),
            text="",
        )

    @staticmethod
    def _pil_rgb_from_bytes(data: bytes) -> Image.Image:
        base = Image.open(io.BytesIO(data))
        if base.mode == "RGBA":
            background = Image.new("RGB", base.size, (40, 40, 40))
            background.paste(base, mask=base.split()[3])
            return background
        return base.convert("RGB")

    def _ctk_image_from_pil(self, img: Image.Image, size: tuple[int, int]) -> ctk.CTkImage:
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
        self._card_thumb_images.append(ctk_img)
        return ctk_img

    def set_thumbnail_bytes(self, data: Optional[bytes]) -> None:
        if not data:
            self._ctk_thumb_image = None
            self._configure_now_thumb(None)
            return
        try:
            base = self._pil_rgb_from_bytes(data)
            self._thumb_pil_light = base.copy()
            self._thumb_pil_dark = base.copy()
            self._ctk_thumb_image = ctk.CTkImage(
                light_image=self._thumb_pil_light,
                dark_image=self._thumb_pil_dark,
                size=THUMB_DISPLAY_SIZE,
            )
            self._configure_now_thumb(self._ctk_thumb_image)
        except Exception:
            self._configure_now_thumb(None)

    def set_now_playing(
        self,
        *,
        active: bool,
        url: str = "",
        title: str = "",
        status: str = "",
        percent: Optional[float] = None,
    ) -> None:
        self._is_downloading = active
        if active:
            display_title = (title or "").strip() or truncate_text(url, 48) or "Baixando…"
            self._now_title_label.configure(text=display_title)
            self._now_url_label.configure(
                text=truncate_text(url, QUEUE_URL_TRUNCATE) if url else ""
            )
            self._now_status_label.configure(
                text=status or DEFAULT_NOW_STATUS
            )
            if percent is not None:
                self._now_progress_bar.set(percent)
                self._now_pct_label.configure(text=f"{int(percent * 100)}%")
            self._now_progress_bar.grid()
            self._now_pct_label.grid()
        else:
            self._now_title_label.configure(text=IDLE_NOW_PLAYING)
            self._now_url_label.configure(text="")
            self._now_status_label.configure(text="")
            self._now_progress_bar.set(0)
            self._now_pct_label.configure(text="0%")
        self._sync_action_buttons()

    def apply_progress_event(self, event: ProgressEvent) -> None:
        if not self._is_downloading:
            return
        if event.event_type == EventType.PROGRESS:
            if event.percent is not None:
                self._now_progress_bar.set(event.percent)
                self._now_pct_label.configure(text=f"{int(event.percent * 100)}%")
            if event.message:
                self._now_status_label.configure(text=event.message)
            if event.title:
                self._now_title_label.configure(text=event.title)
        elif event.event_type == EventType.LOG:
            if event.message:
                self._now_status_label.configure(text=event.message)
            if event.percent is not None:
                self._now_progress_bar.set(event.percent)
                self._now_pct_label.configure(text=f"{int(event.percent * 100)}%")
            if event.title:
                self._now_title_label.configure(text=event.title)
        elif event.event_type == EventType.DONE:
            self._now_progress_bar.set(1.0)
            self._now_pct_label.configure(text="100%")
            if event.message:
                self._now_status_label.configure(text=event.message)
        elif event.event_type == EventType.ERROR:
            if event.message:
                self._now_status_label.configure(text=event.message)
        elif event.event_type == EventType.CANCELLED:
            self._now_status_label.configure(text="Cancelando…")

    def _sync_action_buttons(self) -> None:
        pending = len(self._get_queue_snapshot())
        if self._is_downloading:
            self._cancel_btn.configure(
                state="normal",
                fg_color=BTN_SECONDARY,
                hover_color=BTN_SECONDARY_HOVER,
            )
            if pending:
                self._skip_btn.configure(
                    state="normal",
                    fg_color=ACCENT,
                    hover_color=BTN_SECONDARY_HOVER,
                )
            else:
                self._skip_btn.configure(state="disabled", fg_color=BTN_DISABLED)
        else:
            self._cancel_btn.configure(state="disabled", fg_color=BTN_DISABLED)
            self._skip_btn.configure(state="disabled", fg_color=BTN_DISABLED)

    def _update_header_labels(self, count: int) -> None:
        suffix = f" ({count})" if count else ""
        self._pending_title_label.configure(text=f"Na fila{suffix}")
        self._subtitle_label.configure(
            text=(
                f"{count} vídeo(s) aguardando na fila."
                if count
                else "Acompanhe o download atual e os próximos da fila."
            )
        )

    def refresh(self) -> None:
        """Debounced structural sync (enqueue, remove, clear)."""
        if self._structure_refresh_after_id is not None:
            self.after_cancel(self._structure_refresh_after_id)
        self._structure_refresh_after_id = self.after(
            STRUCTURE_DEBOUNCE_MS, self._do_refresh_structure
        )

    def refresh_structure(self) -> None:
        """Immediate structural sync."""
        if self._structure_refresh_after_id is not None:
            self.after_cancel(self._structure_refresh_after_id)
            self._structure_refresh_after_id = None
        self._do_refresh_structure()

    def reconcile_pending(self) -> None:
        """Sync pending cards after pop/advance (no debounce)."""
        self._do_refresh_structure()

    def _do_refresh_structure(self) -> None:
        self._structure_refresh_after_id = None
        if self._pending_scroll is None:
            return

        urls = self._get_queue_snapshot()
        self._update_header_labels(len(urls))
        pending_set = {u.strip() for u in urls}

        for url in list(self._cards_by_url.keys()):
            if url not in pending_set:
                self._destroy_card(url)

        if not urls:
            if self._empty_label is None:
                self._empty_label = ctk.CTkLabel(
                    self._pending_scroll,
                    text="Nenhum link na fila",
                    font=ctk.CTkFont(size=12),
                    text_color=TEXT_MUTED,
                    anchor="w",
                    wraplength=520,
                    justify="left",
                )
                self._empty_label.grid(row=0, column=0, pady=16, padx=8, sticky="w")
            else:
                self._empty_label.grid()
            self._sync_action_buttons()
            return

        if self._empty_label is not None:
            self._empty_label.grid_remove()

        for index, url in enumerate(urls):
            cleaned = url.strip()
            if cleaned not in self._cards_by_url:
                preview = self._get_cached_preview(cleaned)
                self._create_pending_card(index, cleaned, preview)
            else:
                self._reindex_card(cleaned, index)

        self._sync_action_buttons()

    def update_card(self, url: str) -> None:
        cleaned = url.strip()
        ui = self._cards_by_url.get(cleaned)
        if ui is None:
            return
        preview = self._get_cached_preview(cleaned)
        ui.title_label.configure(text=self._card_title(cleaned, preview))
        ui.meta_label.configure(
            text=f"#{ui.index + 1} · {self._card_duration(preview)}"
        )
        self._apply_thumb_to_column(ui.thumb_col, cleaned, preview)

    def _card_title(self, url: str, preview: Optional[VideoPreview]) -> str:
        if preview and preview.title and preview.title.strip():
            return preview.title.strip()
        if self._is_preview_pending(url):
            return LOADING_TITLE
        if self._get_cached_preview(url) is None:
            return LOADING_TITLE
        return truncate_text(url, 52)

    @staticmethod
    def _card_duration(preview: Optional[VideoPreview]) -> str:
        if preview:
            text = format_duration(preview.duration_seconds)
            if text:
                return text
        return "—"

    def _add_thumb_placeholder(self, parent: ctk.CTkFrame) -> None:
        for child in parent.winfo_children():
            child.destroy()
        box = ctk.CTkFrame(
            parent,
            width=CARD_THUMB_SIZE[0],
            height=CARD_THUMB_SIZE[1],
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            corner_radius=6,
        )
        box.pack()
        box.pack_propagate(False)
        ctk.CTkLabel(
            box,
            text="▶",
            font=ctk.CTkFont(size=22),
            text_color=TEXT_SECONDARY,
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _apply_thumb_to_column(
        self,
        thumb_col: ctk.CTkFrame,
        url: str,
        preview: Optional[VideoPreview],
    ) -> None:
        pil_thumb = self._get_card_thumb(url)
        if pil_thumb is not None:
            for child in thumb_col.winfo_children():
                child.destroy()
            ctk_img = self._ctk_image_from_pil(pil_thumb, CARD_THUMB_SIZE)
            ctk.CTkLabel(
                thumb_col,
                text="",
                image=ctk_img,
                width=CARD_THUMB_SIZE[0],
                height=CARD_THUMB_SIZE[1],
            ).pack()
            return
        if preview and preview.thumbnail_bytes:
            try:
                img = pil_rgb_from_bytes(preview.thumbnail_bytes)
                img = img.resize(CARD_THUMB_SIZE, Image.Resampling.LANCZOS)
                for child in thumb_col.winfo_children():
                    child.destroy()
                ctk_img = self._ctk_image_from_pil(img, CARD_THUMB_SIZE)
                ctk.CTkLabel(
                    thumb_col,
                    text="",
                    image=ctk_img,
                    width=CARD_THUMB_SIZE[0],
                    height=CARD_THUMB_SIZE[1],
                ).pack()
                return
            except Exception:
                logger.exception("Falha ao exibir miniatura do card")
        self._add_thumb_placeholder(thumb_col)

    def _create_pending_card(
        self, index: int, url: str, preview: Optional[VideoPreview]
    ) -> None:
        if self._pending_scroll is None:
            return

        card = ctk.CTkFrame(self._pending_scroll, **CARD_STYLE)
        card.grid(row=index, column=0, sticky="ew", pady=4, padx=2)
        card.grid_columnconfigure(1, weight=1)

        thumb_col = ctk.CTkFrame(card, fg_color="transparent")
        thumb_col.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=10, sticky="n")
        self._apply_thumb_to_column(thumb_col, url, preview)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=0, column=1, sticky="ew", pady=(10, 0))
        title_label = ctk.CTkLabel(
            body,
            text=self._card_title(url, preview),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=400,
            justify="left",
        )
        title_label.pack(anchor="w")

        meta_label = ctk.CTkLabel(
            body,
            text=f"#{index + 1} · {self._card_duration(preview)}",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        meta_label.pack(anchor="w", pady=(4, 0))

        ctk.CTkButton(
            card,
            text="🗑",
            width=36,
            height=32,
            command=lambda u=url: self._remove_by_url(u),
            **SECONDARY_BTN,
        ).grid(row=0, column=2, rowspan=2, padx=(4, 10), pady=10, sticky="ne")

        self._cards_by_url[url] = _PendingCardUi(
            frame=card,
            title_label=title_label,
            meta_label=meta_label,
            thumb_col=thumb_col,
            index=index,
        )

    def _reindex_card(self, url: str, index: int) -> None:
        ui = self._cards_by_url.get(url)
        if ui is None:
            return
        ui.index = index
        ui.frame.grid(row=index, column=0, sticky="ew", pady=4, padx=2)
        preview = self._get_cached_preview(url)
        ui.meta_label.configure(
            text=f"#{index + 1} · {self._card_duration(preview)}"
        )

    def _destroy_card(self, url: str) -> None:
        ui = self._cards_by_url.pop(url, None)
        if ui is not None:
            ui.frame.destroy()

    def _remove_by_url(self, url: str) -> None:
        urls = self._get_queue_snapshot()
        cleaned = url.strip()
        try:
            index = next(i for i, u in enumerate(urls) if u.strip() == cleaned)
        except StopIteration:
            return
        self._on_remove_queue_at(index)
