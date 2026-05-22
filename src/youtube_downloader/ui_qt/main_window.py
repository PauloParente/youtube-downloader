"""Main application window (PySide6)."""

from __future__ import annotations

import os
import threading
from dataclasses import replace
from typing import Optional

from PySide6.QtCore import QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.config import APP_TITLE, DEFAULT_DOWNLOADS_DIR
from youtube_downloader.ui_qt.frameless_window import (
    ResizeEdge,
    apply_mouse_resize,
    hit_test_frame_edges,
    setup_window_root,
    try_native_resize_event,
    update_resize_cursor,
)
from youtube_downloader.core.download_history import (
    DownloadHistoryEntry,
    add_history_entry,
    clear_history,
    entry_disk_signature,
    load_history,
    refresh_entries_from_disk,
    remove_history_entry,
    save_history,
    save_history_thumbnail,
)
from youtube_downloader.core.download_queue import DownloadQueue
from youtube_downloader.core.downloader import YoutubeDownloader
from youtube_downloader.core.ffmpeg_utils import is_bundled_ffmpeg
from youtube_downloader.core.logging_config import (
    LOG_CACHE_DIR,
    LOG_DIR,
    get_logger,
)
from youtube_downloader.core.metadata import VideoPreview, fetch_preview, is_youtube_url
from youtube_downloader.core.models import DownloadJob, EventType, ProgressEvent
from youtube_downloader.core.notifications import notify_download_complete
from youtube_downloader.core.path_utils import open_path_in_explorer
from youtube_downloader.core.preview_cache import PreviewCache
from youtube_downloader.core.queue_coordinator import (
    is_terminal_download_event,
    should_start_next_job,
    should_sync_queue_structure,
)
from youtube_downloader.core.appearance import normalize_appearance_mode
from youtube_downloader.core.settings import AppSettings, load_settings, save_settings
from youtube_downloader.ui_qt.about_dialog import show_about_dialog
from youtube_downloader.ui_qt.download_worker import start_download_thread
from youtube_downloader.ui_qt.downloads_view import DownloadsView
from youtube_downloader.ui_qt.event_bridge import EventBridge
from youtube_downloader.ui_qt.custom_title_bar import CustomTitleBar
from youtube_downloader.ui_qt.nav_registry import DEFAULT_VIEW_ID, stack_index
from youtube_downloader.ui_qt.nav_shortcuts import NAV_VIEW_SHORTCUTS
from youtube_downloader.ui_qt.nav_sidebar import NavSidebar
from youtube_downloader.ui_qt.widgets.status_banner import create_status_banner_slot
from youtube_downloader.ui_qt.theme import apply_theme
from youtube_downloader.ui_qt.util import run_on_main, schedule

logger = get_logger("app")


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        settings: AppSettings | None = None,
        theme_already_applied: bool = False,
    ) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self._settings = settings if settings is not None else load_settings()
        if not theme_already_applied:
            apply_theme(QApplication.instance(), self._settings.appearance_mode)

        self._lazy_placeholders: dict[str, QWidget] = {}
        self._views_built: set[str] = {"download"}

        self._downloader = YoutubeDownloader()
        self._event_bridge = EventBridge()
        self._event_bridge.progress.connect(self._handle_event)
        self._download_queue = DownloadQueue()
        self._preview_cache = PreviewCache()
        self._preview_cache.on_updated(self._on_preview_cache_updated)
        self._history_entries: list[DownloadHistoryEntry] = load_history()
        self._download_thread: Optional[threading.Thread] = None
        self._ffmpeg_banner_shown = False
        self._view_fade_anim: Optional[QPropertyAnimation] = None
        self._active_download_job: Optional[DownloadJob] = None
        self._qthread = None

        self._downloads_view: Optional[DownloadsView] = None
        self._queue_view: Optional[QueueView] = None
        self._history_view: Optional[HistoryView] = None
        self._library_view: Optional[LibraryView] = None
        self._settings_view: Optional[SettingsView] = None
        self._sidebar: Optional[NavSidebar] = None
        self._title_bar: Optional[CustomTitleBar] = None
        self._stack: Optional[QStackedWidget] = None
        self._ffmpeg_status_timer = False
        self._activity_log_buffer: list[str] = []
        self._resize_edge = ResizeEdge.NONE
        self._resize_start_global: Optional[QPointF] = None
        self._resize_start_geom: Optional[QRect] = None

        self._ensure_downloads_dir()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._build_ui()
        self._bind_shortcuts()
        self._apply_settings(self._settings)

    def schedule_startup_tasks(self) -> None:
        """Deferred work after the window is shown (ffmpeg banner, etc.)."""
        schedule(self, 0, self._check_ffmpeg)

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self._title_bar is not None:
            self._title_bar.sync_maximize_button()
        if event.type() == QEvent.Type.WindowStateChange and self.isMaximized():
            self._end_mouse_resize()

    def nativeEvent(self, eventType, message):  # noqa: N802
        handled = try_native_resize_event(self, eventType, message)
        if handled is not None:
            return handled
        return super().nativeEvent(eventType, message)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._begin_mouse_resize(event):
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._resize_edge != ResizeEdge.NONE and self._resize_start_global is not None:
            self._apply_mouse_resize(event.globalPosition())
            event.accept()
            return
        update_resize_cursor(self, event.globalPosition())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._resize_edge != ResizeEdge.NONE:
            self._end_mouse_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _begin_mouse_resize(self, event: QMouseEvent) -> bool:
        if (
            event.button() != Qt.MouseButton.LeftButton
            or self.isMaximized()
            or not event.globalPosition()
        ):
            return False
        pos = event.globalPosition()
        edge = hit_test_frame_edges(
            self.frameGeometry(),
            int(pos.x()),
            int(pos.y()),
        )
        if edge == ResizeEdge.NONE:
            return False
        self._resize_edge = edge
        self._resize_start_global = pos
        self._resize_start_geom = QRect(self.frameGeometry())
        return True

    def _apply_mouse_resize(self, global_pos: QPointF) -> None:
        if self._resize_start_global is None or self._resize_start_geom is None:
            return
        apply_mouse_resize(
            self,
            self._resize_edge,
            self._resize_start_global,
            self._resize_start_geom,
            global_pos,
            min_width=WINDOW_MIN_WIDTH,
            min_height=WINDOW_MIN_HEIGHT,
        )

    def _end_mouse_resize(self) -> None:
        self._resize_edge = ResizeEdge.NONE
        self._resize_start_global = None
        self._resize_start_geom = None
        self.unsetCursor()

    def _build_ui(self) -> None:
        central = QWidget()
        setup_window_root(central)
        self.setCentralWidget(central)
        from PySide6.QtWidgets import QHBoxLayout

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title_bar = CustomTitleBar(self)
        root.addWidget(self._title_bar)

        title_sep = QFrame()
        title_sep.setObjectName("titleBarDivider")
        title_sep.setFrameShape(QFrame.Shape.NoFrame)
        title_sep.setFixedHeight(1)
        root.addWidget(title_sep)

        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        root.addWidget(body, stretch=1)

        self._sidebar = NavSidebar(
            self._on_nav_select,
            self._show_about,
            on_appearance_changed=self._set_appearance_mode,
        )
        layout.addWidget(self._sidebar)

        sep = QFrame()
        sep.setObjectName("sidebarDivider")
        sep.setFrameShape(QFrame.Shape.NoFrame)
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        content_col = QWidget()
        content_layout = QVBoxLayout(content_col)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self._status_banner_slot, self._status_banner = create_status_banner_slot()
        content_layout.addWidget(self._status_banner_slot)
        self._stack = QStackedWidget()
        content_layout.addWidget(self._stack, stretch=1)
        layout.addWidget(content_col, stretch=1)

        # QStackedWidget index order must match NAV_ITEMS in nav_registry.py
        self._downloads_view = DownloadsView(
            event_bridge=self._event_bridge,
            preview_cache=self._preview_cache,
            on_start_download=self._run_download_job,
            on_cancel_download=self._downloader.cancel,
            on_persist_settings=self._persist_settings,
            on_record_history=self._record_history_from_download_event,
            on_get_app_settings=lambda: self._settings,
            on_enqueue_url=self._enqueue_download_url,
            on_enqueue_urls=self._enqueue_download_urls,
            get_queue_snapshot=self._get_queue_snapshot,
            on_remove_queue_at=self._remove_queue_at,
            on_clear_queue=self._clear_download_queue,
            pop_next_queue_url=self._pop_next_queue_url,
            on_sync_queue_structure=self._sync_queue_structure,
            on_sync_now_playing=self._sync_now_playing_panel,
            on_append_log=self._append_activity_log,
            on_set_activity_clear_enabled=self._set_activity_clear_enabled,
            on_open_queue=lambda: self._switch_view("queue"),
        )
        self._stack.addWidget(self._downloads_view)

        for view_id in ("queue", "library", "history", "settings"):
            placeholder = QWidget()
            self._lazy_placeholders[view_id] = placeholder
            self._stack.addWidget(placeholder)

        self._switch_view(DEFAULT_VIEW_ID)
        self._update_nav_queue_badge()

    def _ensure_view(self, view_id: str) -> None:
        if view_id in self._views_built or self._stack is None:
            return
        index = stack_index(view_id)
        if index is None:
            return
        placeholder = self._lazy_placeholders.get(view_id)
        if placeholder is None:
            return

        if view_id == "queue":
            from youtube_downloader.ui_qt.queue_view import QueueView

            self._queue_view = QueueView(
                get_queue_snapshot=self._get_queue_snapshot,
                get_cached_preview=self._preview_cache.get,
                get_card_thumb=self._preview_cache.get_card_thumb,
                is_preview_pending=self._preview_cache.is_pending,
                on_remove_queue_at=self._remove_queue_at,
                on_cancel_download=lambda: (
                    self._downloads_view.cancel_download()
                    if self._downloads_view
                    else None
                ),
                on_skip_download=lambda: (
                    self._downloads_view.skip_to_next_download()
                    if self._downloads_view
                    else None
                ),
                activity_log_expanded=self._settings.activity_log_expanded,
                on_activity_expanded_changed=self._persist_settings,
            )
            self._flush_activity_log_buffer()
            widget = self._queue_view
        elif view_id == "library":
            from youtube_downloader.ui_qt.library_view import LibraryView

            self._library_view = LibraryView(
                get_output_dir=lambda: self._settings.output_dir,
                on_open_path=self._open_path_in_explorer,
            )
            widget = self._library_view
        elif view_id == "history":
            from youtube_downloader.ui_qt.history_view import HistoryView

            self._history_view = HistoryView(
                on_open_folder=self._open_history_folder,
                on_open_file=self._open_history_file,
                on_redownload=self._redownload_from_history,
                on_remove=self._remove_history_entry,
                on_clear_history=self._clear_history,
            )
            self._history_view.set_entries(self._history_entries)
            widget = self._history_view
        elif view_id == "settings":
            from youtube_downloader.ui_qt.settings_view import SettingsView

            self._settings_view = SettingsView(
                on_save=self._on_settings_saved,
                on_appearance_changed=self._set_appearance_mode,
            )
            self._settings_view.load_settings(self._settings)
            self._settings_view.sync_appearance_mode(self._settings.appearance_mode)
            self._settings_view.refresh_section_icons()
            widget = self._settings_view
        else:
            return

        self._stack.removeWidget(placeholder)
        placeholder.deleteLater()
        del self._lazy_placeholders[view_id]
        self._stack.insertWidget(index, widget)
        self._views_built.add(view_id)

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+V"), self, self._on_ctrl_v)
        QShortcut(QKeySequence("Ctrl+,"), self, self._open_settings)
        for view_id, sequence in NAV_VIEW_SHORTCUTS:
            QShortcut(
                QKeySequence(sequence),
                self,
                lambda vid=view_id: self._switch_view(vid),
            )

    def _append_activity_log(self, message: str) -> None:
        text = (message or "").strip()
        if not text:
            return
        if self._queue_view is not None:
            self._queue_view.append_log(text)
        else:
            self._activity_log_buffer.append(text)

    def _flush_activity_log_buffer(self) -> None:
        if self._queue_view is None or not self._activity_log_buffer:
            return
        for line in self._activity_log_buffer:
            self._queue_view.append_log(line)
        self._activity_log_buffer.clear()

    def _set_activity_clear_enabled(self, enabled: bool) -> None:
        if self._queue_view is not None:
            self._queue_view.set_activity_clear_enabled(enabled)

    def _update_nav_queue_badge(self) -> None:
        if self._sidebar is not None:
            self._sidebar.set_queue_badge(len(self._get_queue_snapshot()))

    def _on_nav_select(self, view_id: str) -> None:
        self._switch_view(view_id)

    def _switch_view(self, view_id: str) -> None:
        if self._stack is None or self._sidebar is None:
            return
        self._ensure_view(view_id)
        index = stack_index(view_id)
        if index is None:
            logger.debug("Ignoring unknown nav view_id: %s", view_id)
            return
        previous = self._stack.currentWidget()
        self._stack.setCurrentIndex(index)
        self._sidebar.set_active(view_id)
        current = self._stack.currentWidget()
        if current is not None and current is not previous:
            self._fade_in_view(current)
        if view_id == "history":
            self._refresh_history_from_disk()
            if self._history_view:
                self._history_view.set_entries(self._history_entries)
        if view_id == "library" and self._library_view:
            self._library_view.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_settings()
        super().closeEvent(event)

    def _on_preview_cache_updated(self, url: str) -> None:
        run_on_main(self, lambda u=url: self._handle_preview_cache_updated(u))

    def _handle_preview_cache_updated(self, url: str) -> None:
        if self._queue_view:
            self._queue_view.update_card(url)
        if self._downloads_view and self._downloads_view.is_downloading:
            cleaned = url.strip()
            if self._downloads_view.current_url.strip() == cleaned:
                preview = self._preview_cache.get(cleaned)
                if preview and preview.title:
                    self._downloads_view.set_now_playing_title(preview.title)
                self._sync_now_playing_panel()

    def _sync_now_playing_panel(self) -> None:
        if self._queue_view is None or self._downloads_view is None:
            return
        meta = self._downloads_view.get_now_playing_meta()
        self._queue_view.set_now_playing(
            active=meta["active"],
            url=meta["url"],
            title=meta["title"],
            status=meta["status"],
            percent=meta["percent"],
        )

    def _sync_queue_structure(self) -> None:
        self._update_nav_queue_badge()
        if self._queue_view:
            self._queue_view.refresh()
            self._sync_now_playing_panel()

    def _prefetch_queue_urls(self, urls: list[str]) -> None:
        if urls:
            self._preview_cache.request(urls)

    def _enqueue_download_url(self, url: str) -> bool:
        added = self._download_queue.add(url)
        if added:
            self._prefetch_queue_urls([url])
            self._sync_queue_structure()
        return added

    def _enqueue_download_urls(self, urls: list[str]) -> int:
        before = set(self._download_queue.snapshot())
        added = self._download_queue.add_many(urls)
        if added:
            new_urls = [u for u in self._download_queue.snapshot() if u not in before]
            self._prefetch_queue_urls(new_urls)
            self._sync_queue_structure()
        return added

    def _get_queue_snapshot(self) -> list[str]:
        return self._download_queue.snapshot()

    def _remove_queue_at(self, index: int) -> None:
        if self._download_queue.remove_at(index):
            self._sync_queue_structure()
            self._append_activity_log(f"Removido da fila (posição {index + 1}).")

    def _clear_download_queue(self) -> None:
        if not self._download_queue.snapshot():
            return
        self._download_queue.clear()
        self._sync_queue_structure()
        self._append_activity_log("Fila esvaziada.")

    def _pop_next_queue_url(self) -> str | None:
        url = self._download_queue.pop_next()
        if url:
            self._sync_queue_structure()
        return url

    def _download_worker_alive(self) -> bool:
        return self._qthread is not None and self._qthread.isRunning()

    def _start_next_queued_if_idle(self) -> None:
        if self._downloads_view is None:
            return
        if self._active_download_job is not None or self._download_worker_alive():
            return
        next_url = self._download_queue.pop_next()
        if not next_url:
            return
        if self._queue_view:
            self._queue_view.reconcile_pending()
        self._downloads_view.continue_queue_for_url(next_url)

    def _add_history_entry(
        self,
        filepath: str,
        title: Optional[str] = None,
        source_url: str = "",
        *,
        channel_name: str = "",
        channel_url: str = "",
        thumbnail_bytes: Optional[bytes] = None,
        thumbnail_path: str = "",
    ) -> None:
        if not os.path.isfile(filepath):
            return
        label = (title or "").strip() or os.path.basename(filepath)
        thumb_path = thumbnail_path
        if not thumb_path and thumbnail_bytes and source_url.strip():
            thumb_path = save_history_thumbnail(source_url, thumbnail_bytes)
        entry = DownloadHistoryEntry.from_filepath(
            filepath,
            label,
            source_url,
            channel_name=channel_name,
            channel_url=channel_url,
            thumbnail_path=thumb_path,
        )
        self._history_entries = add_history_entry(entry)
        if self._history_view and self._sidebar and self._sidebar.active_view_id() == "history":
            self._history_view.set_entries(self._history_entries)

    def _add_history_entry_async(self, **kwargs) -> None:
        def worker() -> None:
            filepath = kwargs.get("filepath", "")
            if not os.path.isfile(filepath):
                return
            thumb_path = ""
            tb = kwargs.get("thumbnail_bytes")
            su = kwargs.get("source_url", "")
            if tb and su.strip():
                thumb_path = save_history_thumbnail(su, tb)
            label = (kwargs.get("title") or "").strip() or os.path.basename(filepath)
            entry = DownloadHistoryEntry.from_filepath(
                filepath,
                label,
                su,
                channel_name=kwargs.get("channel_name", ""),
                channel_url=kwargs.get("channel_url", ""),
                thumbnail_path=thumb_path,
            )
            try:
                entries = add_history_entry(entry)
            except Exception:
                logger.exception("Falha ao gravar historico em background")
                return

            def on_main() -> None:
                self._history_entries = entries
                if (
                    self._history_view
                    and self._sidebar
                    and self._sidebar.active_view_id() == "history"
                ):
                    self._history_view.set_entries(entries)

            run_on_main(self, on_main)

        threading.Thread(target=worker, daemon=True).start()

    def _record_history_from_download_event(self, event: ProgressEvent) -> None:
        filepath = event.filepath
        if not filepath or not os.path.isfile(filepath) or not self._downloads_view:
            return
        source_url = self._downloads_view.current_url
        meta = self._preview_cache.get(source_url)
        defer_disk = bool(self._download_queue.snapshot())

        def build_fields(preview: Optional[VideoPreview]) -> dict:
            title = (event.title or "").strip()
            if not title and preview and preview.title:
                title = preview.title.strip()
            if not title:
                title = os.path.basename(filepath)
            return {
                "filepath": filepath,
                "title": title,
                "source_url": source_url,
                "channel_name": (preview.uploader or "").strip() if preview else "",
                "channel_url": (preview.channel_url or "").strip() if preview else "",
                "thumbnail_bytes": (
                    preview.thumbnail_bytes if preview and preview.thumbnail_bytes else None
                ),
            }

        def resolve_preview() -> Optional[VideoPreview]:
            if meta is not None and not meta.error:
                return meta
            if not source_url or not is_youtube_url(source_url):
                return None
            try:
                fetched = fetch_preview(source_url)
            except Exception:
                logger.exception("Metadados do historico (fallback): %s", source_url[:80])
                return None
            if fetched and not fetched.error:
                self._preview_cache.put(fetched)
                return fetched
            return None

        if defer_disk:
            def worker() -> None:
                fields = build_fields(resolve_preview())
                self._add_history_entry_async(**fields)

            threading.Thread(target=worker, daemon=True).start()
            return

        fields = build_fields(meta if meta and not meta.error else None)
        if fields["thumbnail_bytes"] is None and source_url and is_youtube_url(source_url):

            def worker() -> None:
                resolved = build_fields(resolve_preview())
                run_on_main(self, lambda f=resolved: self._add_history_entry(**f))

            threading.Thread(target=worker, daemon=True).start()
            return

        self._add_history_entry(**fields)

    def _open_history_folder(self, filepath: str) -> None:
        if os.path.isfile(filepath):
            folder = os.path.dirname(filepath)
            if os.path.isdir(folder):
                self._open_path_in_explorer(folder)
        elif os.path.isdir(filepath):
            self._open_path_in_explorer(filepath)

    def _open_history_file(self, filepath: str) -> None:
        if os.path.isfile(filepath):
            self._open_path_in_explorer(filepath)

    def _redownload_from_history(self, url: str, _title: str) -> None:
        cleaned = url.strip()
        if not cleaned:
            return
        self._switch_view(DEFAULT_VIEW_ID)
        if self._downloads_view:
            self._downloads_view.set_url_and_focus(cleaned)
            self._downloads_view.show_status_hint(
                "URL do histórico colada. Clique em Baixar para iniciar."
            )

    def _refresh_history_from_disk(self) -> None:
        refreshed = refresh_entries_from_disk(self._history_entries)
        old_sig = [entry_disk_signature(e) for e in self._history_entries]
        new_sig = [entry_disk_signature(e) for e in refreshed]
        if old_sig != new_sig:
            self._history_entries = refreshed
            save_history(refreshed)

    def _clear_history(self) -> list[DownloadHistoryEntry]:
        self._history_entries = clear_history()
        return self._history_entries

    def _remove_history_entry(self, filepath: str) -> list[DownloadHistoryEntry]:
        self._history_entries = remove_history_entry(filepath)
        return self._history_entries

    def _on_ctrl_v(self) -> None:
        if self._downloads_view and not self._downloads_view.is_downloading:
            self._downloads_view.paste_url()

    def _open_settings(self) -> None:
        if self._downloads_view and self._downloads_view.is_downloading:
            return
        self._switch_view("settings")
        if self._settings_view:
            self._settings_view.load_settings(self._settings)

    def _on_settings_saved(self, settings: AppSettings) -> None:
        if self._downloads_view and self._downloads_view.is_downloading:
            return
        self._settings = settings
        save_settings(settings)
        self._apply_settings(settings)

    def _show_temporary_status(self, message: str, delay_ms: int = 8000) -> None:
        if self._downloads_view:
            self._downloads_view.set_download_status(message)
        schedule(self, delay_ms, self._clear_temporary_status)

    def _clear_temporary_status(self) -> None:
        if self._downloads_view and not self._downloads_view.is_downloading:
            self._downloads_view.reset_download_status()

    def _ensure_downloads_dir(self) -> None:
        DEFAULT_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    def _fade_in_view(self, widget: QWidget) -> None:
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._view_fade_anim = anim

        def _cleanup() -> None:
            widget.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        anim.start()

    def _check_ffmpeg(self) -> None:
        if self._ffmpeg_banner_shown or is_bundled_ffmpeg():
            return
        if YoutubeDownloader.ffmpeg_available():
            self._status_banner.show_message(
                "Aviso: FFmpeg do sistema. Para distribuir o app, use .\\build.ps1."
            )
        else:
            self._status_banner.show_message(
                "FFmpeg não encontrado. Use build.ps1 ou instale FFmpeg no PATH."
            )
        self._ffmpeg_banner_shown = True

    def _set_appearance_mode(self, mode: str) -> None:
        mode = normalize_appearance_mode(mode, self._settings.appearance_mode)
        if mode == self._settings.appearance_mode:
            return
        self._settings = replace(self._settings, appearance_mode=mode)
        save_settings(self._settings)
        apply_theme(QApplication.instance(), mode)
        if self._title_bar is not None:
            self._title_bar.refresh_control_icons()
        if self._sidebar is not None:
            self._sidebar.set_appearance_mode(mode)
            self._sidebar.refresh_theme()
        if self._settings_view is not None:
            self._settings_view.sync_appearance_mode(mode)
            self._settings_view.refresh_section_icons()

    def _apply_settings(self, settings: AppSettings) -> None:
        apply_theme(QApplication.instance(), settings.appearance_mode)
        if self._title_bar is not None:
            self._title_bar.refresh_control_icons()
        if self._sidebar is not None:
            self._sidebar.set_appearance_mode(settings.appearance_mode)
            self._sidebar.refresh_theme()
        if self._downloads_view:
            self._downloads_view.apply_settings(settings)
        if self._queue_view:
            self._queue_view.apply_activity_settings(
                activity_log_expanded=settings.activity_log_expanded,
            )
        if self._settings_view:
            self._settings_view.load_settings(settings)
            self._settings_view.refresh_section_icons()

    def _persist_settings(self) -> None:
        if self._downloads_view is None:
            return
        collected = self._downloads_view.collect_settings()
        activity_expanded = (
            self._queue_view.activity_log_expanded()
            if self._queue_view is not None
            else collected.activity_log_expanded
        )
        self._settings = replace(
            self._settings,
            output_dir=collected.output_dir,
            quality=collected.quality,
            audio_only=collected.audio_only,
            activity_log_expanded=activity_expanded,
        )
        save_settings(self._settings)

    def _show_about(self) -> None:
        try:
            show_about_dialog(self, on_open_logs=self._open_logs)
        except Exception:
            logger.exception("Falha ao abrir diálogo Sobre")

    def _open_path_in_explorer(self, path: str) -> None:
        try:
            open_path_in_explorer(path)
        except OSError as exc:
            logger.exception("Falha ao abrir caminho: %s", path)
            if self._downloads_view:
                self._downloads_view.set_download_status(f"Erro ao abrir: {exc}")

    def _open_logs(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._open_path_in_explorer(str(LOG_DIR))

    def _run_download_job(self, job: DownloadJob) -> None:
        if self._downloads_view is None:
            return
        if self._download_worker_alive():
            logger.warning(
                "Download ignorado: thread anterior ainda ativa para %s",
                (self._active_download_job.url if self._active_download_job else job.url),
            )
            return
        self._active_download_job = job
        self._switch_view("queue")
        self._qthread = start_download_thread(
            self._downloader,
            job,
            on_progress=self._event_bridge.emit_progress,
            on_finished=self._on_download_worker_finished,
        )

    def _on_download_worker_finished(self) -> None:
        self._qthread = None
        if self._downloads_view is None or not self._downloads_view.is_downloading:
            return
        if self._download_worker_alive() or self._active_download_job is not None:
            return
        if self._download_queue.snapshot():
            self._start_next_queued_if_idle()
            return
        logger.warning(
            "Worker terminou com UI em modo download sem fila; recuperando controles"
        )
        self._downloads_view.force_release_download_ui()

    def _handle_event(self, event: ProgressEvent) -> None:
        try:
            if self._downloads_view:
                self._downloads_view.handle_progress_event(event)
            if self._queue_view and self._downloads_view:
                if event.event_type in (
                    EventType.PROGRESS,
                    EventType.LOG,
                    EventType.DONE,
                    EventType.ERROR,
                    EventType.CANCELLED,
                ):
                    self._sync_now_playing_panel()
                self._queue_view.apply_progress_event(event)
                if is_terminal_download_event(event.event_type):
                    continue_after_cancel = False
                    is_downloading = self._downloads_view.is_downloading
                    if is_downloading and event.event_type == EventType.CANCELLED:
                        continue_after_cancel = (
                            self._downloads_view.should_continue_queue_after_cancel()
                        )
                    if should_sync_queue_structure(
                        event.event_type,
                        is_downloading=is_downloading,
                        queue_has_items=bool(self._get_queue_snapshot()),
                        continue_after_cancel=continue_after_cancel,
                    ):
                        self._sync_queue_structure()

            job = self._active_download_job
            if job is None:
                return

            if event.event_type == EventType.DONE:
                try:
                    if job.notify_on_complete:
                        name = event.title or (
                            os.path.basename(event.filepath)
                            if event.filepath
                            else "Download"
                        )
                        notify_download_complete(APP_TITLE, f"Download concluído: {name}")
                except Exception:
                    logger.exception("Falha ao exibir notificacao de download")
                self._active_download_job = None
                self._start_next_queued_if_idle()
            elif event.event_type == EventType.CANCELLED:
                self._active_download_job = None
                continue_after_cancel = (
                    self._downloads_view is not None
                    and self._downloads_view.should_continue_queue_after_cancel()
                )
                if should_start_next_job(
                    event.event_type, continue_after_cancel=continue_after_cancel
                ):
                    self._start_next_queued_if_idle()
            elif event.event_type == EventType.ERROR:
                self._active_download_job = None
        except Exception:
            logger.exception("Erro ao processar evento: %s", event.event_type.value)
            if self._downloads_view and event.event_type in (
                EventType.DONE,
                EventType.ERROR,
                EventType.CANCELLED,
            ):
                self._downloads_view.force_release_download_ui()
            self._active_download_job = None


def run() -> None:
    """Backward-compatible entry; prefer youtube_downloader.ui_qt.startup.run."""
    from youtube_downloader.ui_qt.startup import run as startup_run

    startup_run()
