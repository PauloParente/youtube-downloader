"""Left navigation sidebar."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.icons import icon_on_button
from youtube_downloader.ui_qt.nav_registry import DEFAULT_VIEW_ID, NAV_ITEMS
from youtube_downloader.ui_qt.nav_shortcuts import format_queue_badge, nav_tooltip
from youtube_downloader.ui_qt.theme import polish_widget
from youtube_downloader.ui_qt.theme_tokens import SIDEBAR_WIDTH
from youtube_downloader.ui_qt.widgets import Separator
from youtube_downloader.ui_qt.widgets.nav_button import NavButton
from youtube_downloader.ui_qt.widgets.nav_list import NavListWidget


class NavSidebar(QFrame):
    # Backward-compatible tuple for tests and docs: (view_id, icon, label)
    ITEMS = tuple((item.view_id, item.icon, item.label) for item in NAV_ITEMS)

    def __init__(
        self,
        on_select: Callable[[str], None],
        on_about: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self._on_select = on_select
        self._on_about = on_about
        self._active_id = DEFAULT_VIEW_ID
        self._icon_names: dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 16)
        layout.setSpacing(6)

        self._nav_list = NavListWidget()
        layout.addWidget(self._nav_list)

        self._queue_badge = QLabel()
        self._queue_badge.setObjectName("navBadge")
        self._queue_badge.setAutoFillBackground(False)
        self._queue_badge.setProperty("active", "false")
        self._queue_badge.setProperty("empty", "true")
        polish_widget(self._queue_badge)

        for item in NAV_ITEMS:
            btn = NavButton(item.label)
            btn.setToolTip(nav_tooltip(item.label, item.view_id))
            icon_on_button(btn, item.icon, size=18)
            self._icon_names[item.view_id] = item.icon
            btn.clicked.connect(lambda checked, vid=item.view_id: self._select(vid))
            badge = self._queue_badge if item.view_id == "queue" else None
            self._nav_list.add_item(item.view_id, btn, badge=badge)

        layout.addStretch()

        layout.addWidget(Separator())
        about_btn = NavButton("Sobre", focusable=False)
        about_btn.setToolTip("Sobre")
        icon_on_button(about_btn, "about", size=18)
        about_btn.clicked.connect(on_about)
        about_btn.setFixedHeight(40)
        layout.addWidget(about_btn)

    def active_view_id(self) -> str:
        return self._active_id

    def _select(self, view_id: str) -> None:
        self._on_select(view_id)

    def _sync_nav_icons(self) -> None:
        for view_id, icon_name in self._icon_names.items():
            row = self._nav_list.row_for(view_id)
            if row is None:
                continue
            accent = view_id == self._active_id
            icon_on_button(row.button, icon_name, size=18, accent=accent)

    def _sync_queue_badge_style(self) -> None:
        has_count = bool(self._queue_badge.text())
        active = self._active_id == "queue" and has_count
        self._queue_badge.setProperty("active", "true" if active else "false")
        polish_widget(self._queue_badge)

    def set_queue_badge(self, count: int) -> None:
        text = format_queue_badge(count) or ""
        self._queue_badge.setText(text)
        self._queue_badge.setProperty("empty", "true" if not text else "false")
        polish_widget(self._queue_badge)
        self._sync_queue_badge_style()

    def set_active(self, view_id: str) -> None:
        if view_id not in self._icon_names:
            return
        changed = view_id != self._active_id
        self._active_id = view_id
        self._nav_list.set_active(
            view_id,
            animate=changed,
            on_icon_sync=self._sync_nav_icons,
        )
        self._sync_queue_badge_style()

    def refresh_theme(self) -> None:
        self._sync_nav_icons()
        for button in self._nav_list.iter_buttons():
            button.update()
