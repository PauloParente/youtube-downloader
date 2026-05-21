"""Preview panel for the Downloads screen (thumbnail, title, debounced fetch)."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Optional

import customtkinter as ctk
from PIL import Image

from youtube_downloader.core.logging_config import (
    LOG_CACHE_DIR,
    clear_preview_cache,
    get_logger,
)
from youtube_downloader.core.metadata import (
    VideoPreview,
    fetch_preview,
    format_duration,
    is_youtube_url,
)
from youtube_downloader.core.models import EventType, ProgressEvent
from youtube_downloader.core.preview_cache import PreviewCache, pil_rgb_from_bytes
from youtube_downloader.ui.theme import (
    CARD_BORDER,
    CARD_STYLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

logger = get_logger(__name__)

PREVIEW_DEBOUNCE_MS = 600
THUMB_DISPLAY_SIZE = (240, 135)


class DownloadsPreviewPanel:
    """URL preview UI and debounced metadata fetch."""

    def __init__(
        self,
        host: ctk.CTkBaseClass,
        *,
        url_entry: ctk.CTkEntry,
        event_queue: queue.Queue[ProgressEvent],
        preview_cache: PreviewCache,
        is_downloading: Callable[[], bool],
    ) -> None:
        self._host = host
        self._url_entry = url_entry
        self._event_queue = event_queue
        self._preview_cache = preview_cache
        self._is_downloading = is_downloading

        self._preview_after_id: Optional[str] = None
        self._preview_request_id = 0
        self._current_preview: Optional[VideoPreview] = None
        self._ctk_preview_image: Optional[ctk.CTkImage] = None
        self._preview_pil_light: Optional[Image.Image] = None
        self._preview_pil_dark: Optional[Image.Image] = None
        self._placeholder_image: Optional[ctk.CTkImage] = None
        self._placeholder_pil_light: Optional[Image.Image] = None
        self._placeholder_pil_dark: Optional[Image.Image] = None

        self._mid: Optional[ctk.CTkFrame] = None
        self._preview_placeholder: Optional[ctk.CTkFrame] = None
        self._preview_frame: Optional[ctk.CTkFrame] = None
        self._thumb_label: Optional[ctk.CTkLabel] = None
        self._thumb_duration_label: Optional[ctk.CTkLabel] = None
        self._preview_title_label: Optional[ctk.CTkLabel] = None
        self._preview_subtitle_label: Optional[ctk.CTkLabel] = None

    @property
    def current_preview(self) -> Optional[VideoPreview]:
        return self._current_preview

    @property
    def mid(self) -> Optional[ctk.CTkFrame]:
        return self._mid

    @property
    def preview_title_label(self) -> Optional[ctk.CTkLabel]:
        return self._preview_title_label

    @property
    def preview_frame(self) -> Optional[ctk.CTkFrame]:
        return self._preview_frame

    def build_into(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """Create placeholder + preview card; return the card frame for extra controls."""
        self._mid = parent
        parent.grid_columnconfigure(0, weight=1)

        self._preview_placeholder = ctk.CTkFrame(parent, **CARD_STYLE)
        self._preview_placeholder.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            self._preview_placeholder,
            text="O preview do vídeo aparecerá aqui",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=12),
        ).place(relx=0.5, rely=0.5, anchor="center")

        self._preview_frame = ctk.CTkFrame(parent, **CARD_STYLE)
        self._preview_frame.grid_remove()
        self._preview_frame.grid_columnconfigure(0, weight=1)

        thumb_wrap = ctk.CTkFrame(self._preview_frame, fg_color="transparent")
        thumb_wrap.pack(fill="x", padx=12, pady=(12, 8))
        self._thumb_label = ctk.CTkLabel(
            thumb_wrap,
            text="",
            width=THUMB_DISPLAY_SIZE[0],
            height=THUMB_DISPLAY_SIZE[1],
            fg_color=("#2a2a2a", "#2a2a2a"),
            corner_radius=6,
        )
        self._thumb_label.pack(anchor="w")
        self._ensure_placeholder_image()
        self._thumb_duration_label = ctk.CTkLabel(
            thumb_wrap,
            text="",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=("#000000", "#000000"),
            corner_radius=4,
            width=44,
            height=20,
        )
        self._thumb_duration_label.place(
            x=THUMB_DISPLAY_SIZE[0] - 52, y=THUMB_DISPLAY_SIZE[1] - 28
        )
        self._preview_title_label = ctk.CTkLabel(
            self._preview_frame,
            text="",
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        self._preview_title_label.pack(fill="x", padx=12, pady=(0, 4))
        self._preview_subtitle_label = ctk.CTkLabel(
            self._preview_frame,
            text="",
            anchor="w",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
        )
        self._preview_subtitle_label.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkFrame(
            self._preview_frame,
            height=1,
            fg_color=CARD_BORDER,
            corner_radius=0,
        ).pack(fill="x", padx=12, pady=(0, 12))

        assert self._preview_frame is not None
        return self._preview_frame

    def clear(self) -> None:
        self._clear_preview()

    def cancel_pending_schedule(self) -> None:
        if self._preview_after_id is not None:
            self._host.after_cancel(self._preview_after_id)
            self._preview_after_id = None

    def schedule_preview(self) -> None:
        if self._is_downloading():
            return
        self.cancel_pending_schedule()
        self._preview_after_id = self._host.after(
            PREVIEW_DEBOUNCE_MS, self._run_preview_fetch
        )

    def handle_progress_event(self, event: ProgressEvent) -> bool:
        """Apply PREVIEW_* events. Returns True if handled."""
        if event.event_type == EventType.PREVIEW_READY:
            if event.preview is not None and event.preview_url:
                self._apply_preview(
                    event.preview,
                    event.preview_url,
                    request_id=event.preview_request_id,
                )
            return True
        if event.event_type == EventType.PREVIEW_CLEAR:
            self._clear_preview()
            return True
        return False

    def _run_preview_fetch(self) -> None:
        self._preview_after_id = None
        if self._is_downloading():
            return

        url = self._url_entry.get().strip()
        if not url or not is_youtube_url(url):
            logger.debug("preview ignorado: URL vazia ou não-YouTube")
            self._clear_preview()
            return

        self._preview_request_id += 1
        request_id = self._preview_request_id
        logger.debug("preview agendado request_id=%s url=%s", request_id, url)
        self._show_preview_loading()

        def worker() -> None:
            logger.debug("preview fetch iniciado request_id=%s", request_id)
            preview = fetch_preview(url)
            logger.debug(
                "preview fetch fim request_id=%s erro=%s thumb=%s",
                request_id,
                bool(preview.error),
                len(preview.thumbnail_bytes) if preview.thumbnail_bytes else 0,
            )
            self._event_queue.put(
                ProgressEvent(
                    event_type=EventType.PREVIEW_READY,
                    preview=preview,
                    preview_url=url,
                    preview_request_id=request_id,
                )
            )

        threading.Thread(target=worker, daemon=True).start()

    def _show_preview_panel(self, visible: bool) -> None:
        if self._preview_frame is None or self._preview_placeholder is None:
            return
        if visible:
            self._preview_frame.grid(row=0, column=0, sticky="ew")
            self._preview_placeholder.grid_remove()
        else:
            self._preview_frame.grid_remove()
            self._preview_placeholder.grid(row=0, column=0, sticky="ew")

    def _ensure_placeholder_image(self) -> ctk.CTkImage:
        if self._placeholder_image is not None:
            return self._placeholder_image
        gray = Image.new("RGB", THUMB_DISPLAY_SIZE, (64, 64, 64))
        self._placeholder_pil_light = gray.copy()
        self._placeholder_pil_dark = gray.copy()
        self._placeholder_image = ctk.CTkImage(
            light_image=self._placeholder_pil_light,
            dark_image=self._placeholder_pil_dark,
            size=THUMB_DISPLAY_SIZE,
        )
        return self._placeholder_image

    def _configure_thumb(self, image: Optional[ctk.CTkImage], text: str) -> None:
        if self._thumb_label is None:
            return
        self._thumb_label.configure(
            image=image if image is not None else self._ensure_placeholder_image(),
            text=text,
        )

    def _release_preview_images(self) -> None:
        self._ctk_preview_image = None
        self._preview_pil_light = None
        self._preview_pil_dark = None

    def _detach_thumb_image(self) -> None:
        self._configure_thumb(None, "")
        self._release_preview_images()

    def _show_preview_loading(self) -> None:
        clear_preview_cache()
        self._show_preview_panel(True)
        self._detach_thumb_image()
        self._configure_thumb(None, "…")
        if self._preview_title_label is not None:
            self._preview_title_label.configure(text="Carregando preview…")
        if self._preview_subtitle_label is not None:
            self._preview_subtitle_label.configure(text="")

    def _clear_preview(self) -> None:
        self._preview_request_id += 1
        self._current_preview = None
        clear_preview_cache()
        self._detach_thumb_image()
        self._configure_thumb(None, "")
        if self._preview_title_label is not None:
            self._preview_title_label.configure(text="")
        if self._preview_subtitle_label is not None:
            self._preview_subtitle_label.configure(text="")
        if self._thumb_duration_label is not None:
            self._thumb_duration_label.configure(text="")
        self._show_preview_panel(False)

    def _apply_preview(
        self,
        preview: VideoPreview,
        url: str,
        request_id: Optional[int] = None,
    ) -> None:
        if request_id is not None and request_id != self._preview_request_id:
            logger.warning(
                "preview obsoleto ignorado: request_id=%s atual=%s",
                request_id,
                self._preview_request_id,
            )
            return
        if self._url_entry.get().strip() != url:
            logger.warning(
                "preview URL divergente ignorado: esperado=%r campo=%r",
                url,
                self._url_entry.get().strip(),
            )
            return

        if not preview.error:
            self._preview_cache.put(preview)

        if self._is_downloading():
            return

        logger.debug(
            "apply_preview request_id=%s title=%r bytes=%s",
            request_id,
            preview.title[:50] if preview.title else "",
            len(preview.thumbnail_bytes) if preview.thumbnail_bytes else 0,
        )

        if preview.error:
            logger.error("preview erro: %s | url=%s", preview.error, url)
            self._show_preview_panel(True)
            self._detach_thumb_image()
            self._configure_thumb(None, "?")
            if self._preview_title_label is not None:
                self._preview_title_label.configure(text="Preview indisponível")
            if self._preview_subtitle_label is not None:
                self._preview_subtitle_label.configure(text=preview.error[:120])
            return

        self._current_preview = preview
        self._show_preview_panel(True)
        if self._preview_title_label is not None:
            self._preview_title_label.configure(text=preview.title)

        if preview.is_playlist and preview.playlist_count is not None:
            if self._preview_subtitle_label is not None:
                self._preview_subtitle_label.configure(
                    text=f"Playlist · {preview.playlist_count} vídeos"
                )
        else:
            channel = preview.uploader or "Canal"
            duration = format_duration(preview.duration_seconds)
            if self._preview_subtitle_label is not None:
                self._preview_subtitle_label.configure(
                    text=f"{channel} · {duration}" if duration else channel
                )

        duration_text = format_duration(preview.duration_seconds)
        if self._thumb_duration_label is not None:
            self._thumb_duration_label.configure(text=duration_text or "")

        if preview.thumbnail_bytes:
            try:
                cache_id = (
                    request_id if request_id is not None else self._preview_request_id
                )
                cache_path = LOG_CACHE_DIR / f"preview_{cache_id}.jpg"
                base = pil_rgb_from_bytes(preview.thumbnail_bytes)
                base.save(cache_path, "JPEG", quality=90)

                self._preview_pil_light = base.copy()
                self._preview_pil_dark = base.copy()
                self._ctk_preview_image = ctk.CTkImage(
                    light_image=self._preview_pil_light,
                    dark_image=self._preview_pil_dark,
                    size=THUMB_DISPLAY_SIZE,
                )
                self._configure_thumb(self._ctk_preview_image, "")
                logger.debug(
                    "thumbnail exibida request_id=%s cache=%s size=%s",
                    cache_id,
                    cache_path,
                    base.size,
                )
            except Exception:
                logger.exception(
                    "Falha ao exibir thumbnail request_id=%s url=%s",
                    request_id,
                    url,
                )
                self._detach_thumb_image()
                self._configure_thumb(None, "?")
        else:
            logger.warning(
                "preview sem thumbnail_bytes request_id=%s url=%s", request_id, url
            )
            self._detach_thumb_image()
            self._configure_thumb(None, "?")
