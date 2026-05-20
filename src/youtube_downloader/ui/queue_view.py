"""Fila de downloads — download atual e pendentes."""

from __future__ import annotations

import io
from collections.abc import Callable
from typing import Optional

import customtkinter as ctk
from PIL import Image

from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui.theme import (
    ACCENT,
    BTN_DISABLED,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    CARD_STYLE,
    SECONDARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

THUMB_DISPLAY_SIZE = (240, 135)
QUEUE_URL_TRUNCATE = 58
PENDING_SCROLL_HEIGHT = 280
IDLE_NOW_PLAYING = "Nenhum download em andamento"
DEFAULT_NOW_STATUS = "Aguardando…"


class QueueView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        get_queue_snapshot: Callable[[], list[str]],
        on_remove_queue_at: Callable[[int], None],
        on_cancel_download: Callable[[], None],
        on_skip_download: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._get_queue_snapshot = get_queue_snapshot
        self._on_remove_queue_at = on_remove_queue_at
        self._on_cancel_download = on_cancel_download
        self._on_skip_download = on_skip_download

        self._is_downloading = False
        self._pending_rows_inner: Optional[ctk.CTkFrame] = None
        self._ctk_thumb_image: Optional[ctk.CTkImage] = None
        self._thumb_pil_light: Optional[Image.Image] = None
        self._thumb_pil_dark: Optional[Image.Image] = None
        self._placeholder_image: Optional[ctk.CTkImage] = None

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

        self.refresh()

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

        self._pending_rows_inner = ctk.CTkFrame(self._pending_scroll, fg_color="transparent")
        self._pending_rows_inner.grid(row=0, column=0, sticky="ew")
        self._pending_rows_inner.grid_columnconfigure(1, weight=1)

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

    def refresh(self) -> None:
        pending = self._get_queue_snapshot()
        count = len(pending)
        suffix = f" ({count})" if count else ""
        self._pending_title_label.configure(text=f"Na fila{suffix}")
        self._subtitle_label.configure(
            text=(
                f"{count} vídeo(s) aguardando na fila."
                if count
                else "Acompanhe o download atual e os próximos da fila."
            )
        )
        self._render_pending_rows(pending)
        self._sync_action_buttons()

    def _render_pending_rows(self, urls: list[str]) -> None:
        if self._pending_rows_inner is None:
            return
        for child in self._pending_rows_inner.winfo_children():
            child.destroy()

        if not urls:
            ctk.CTkLabel(
                self._pending_rows_inner,
                text="Nenhum link na fila",
                font=ctk.CTkFont(size=11),
                text_color=TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=8)
            return

        for index, url in enumerate(urls):
            row = ctk.CTkFrame(self._pending_rows_inner, fg_color="transparent")
            row.grid(row=index, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row,
                text=f"{index + 1}.",
                width=22,
                font=ctk.CTkFont(size=11),
                text_color=TEXT_MUTED,
                anchor="e",
            ).grid(row=0, column=0, padx=(0, 6))

            ctk.CTkLabel(
                row,
                text=truncate_text(url, QUEUE_URL_TRUNCATE),
                font=ctk.CTkFont(size=11),
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).grid(row=0, column=1, sticky="ew")

            ctk.CTkButton(
                row,
                text="🗑",
                width=36,
                height=28,
                command=lambda i=index: self._remove_queue_item(i),
                **SECONDARY_BTN,
            ).grid(row=0, column=2, padx=(6, 0))

    def _remove_queue_item(self, index: int) -> None:
        self._on_remove_queue_at(index)
