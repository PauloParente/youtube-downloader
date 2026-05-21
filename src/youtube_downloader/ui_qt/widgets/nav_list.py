"""Nav list with sliding selection pill."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from youtube_downloader.ui_qt.nav_anim import lerp_hex_color, nav_row_highlight_rectf, pill_geometry_for_row
from youtube_downloader.ui_qt.theme import current_appearance_palette
from youtube_downloader.ui_qt.theme_tokens import (
    NAV_ANIM_SELECT_MS,
    NAV_BADGE_SLOT_WIDTH,
    NAV_ICON_SYNC_RATIO,
    NAV_ITEM_HEIGHT,
    RADIUS_BUTTON,
)
from youtube_downloader.ui_qt.widgets.nav_button import NavButton


class NavItemRow(QWidget):
    """Single row: nav button + reserved badge column (same width on every row)."""

    def __init__(
        self,
        view_id: str,
        button: NavButton,
        parent: QWidget | None = None,
        *,
        badge: QLabel | None = None,
    ) -> None:
        super().__init__(parent)
        self.view_id = view_id
        self.button = button
        self.badge = badge
        self.setFixedHeight(NAV_ITEM_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(button, stretch=1)
        button._hover_anim.valueChanged.connect(lambda _v: self.update())

        if badge is not None:
            slot = QWidget(self)
            slot.setObjectName("navBadgeSlot")
            slot.setAutoFillBackground(False)
            slot.setFixedWidth(NAV_BADGE_SLOT_WIDTH)
            slot_layout = QHBoxLayout(slot)
            slot_layout.setContentsMargins(0, 0, 4, 0)
            slot_layout.setSpacing(0)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(slot)
        else:
            layout.addSpacing(NAV_BADGE_SLOT_WIDTH)

    def paintEvent(self, event) -> None:  # noqa: N802
        btn = self.button
        palette = current_appearance_palette()
        rect = nav_row_highlight_rectf(self.width(), self.height())
        needs_paint = (
            (not btn.is_nav_active() and btn._hover_t > 0.001)
            or (btn.hasFocus() and not btn.is_nav_active())
        )
        if needs_paint:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            if not btn.is_nav_active() and btn._hover_t > 0.001:
                bg = lerp_hex_color(
                    palette.sidebar_bg, palette.btn_secondary, btn._hover_t
                )
                path = QPainterPath()
                path.addRoundedRect(rect, RADIUS_BUTTON, RADIUS_BUTTON)
                painter.fillPath(path, QColor(bg))
            if btn.hasFocus() and not btn.is_nav_active():
                painter.setPen(QPen(QColor(palette.focus_border), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect, RADIUS_BUTTON, RADIUS_BUTTON)
            painter.end()
        super().paintEvent(event)


class NavListWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: dict[str, NavItemRow] = {}
        self._active_id: str | None = None
        self._pill_anim: QPropertyAnimation | None = None
        self._icon_sync_pending: Callable[[], None] | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

        self._pill = QFrame(self)
        self._pill.setObjectName("navPill")
        self._pill.lower()

    def add_item(
        self,
        view_id: str,
        button: NavButton,
        *,
        badge: QLabel | None = None,
    ) -> NavItemRow:
        row = NavItemRow(view_id, button, self, badge=badge)
        self._rows[view_id] = row
        self._layout.addWidget(row)
        return row

    def row_for(self, view_id: str) -> NavItemRow | None:
        return self._rows.get(view_id)

    def iter_buttons(self):
        """Yield each nav button in registration order."""
        for item in self._rows.values():
            yield item.button

    def set_active(
        self,
        view_id: str,
        *,
        animate: bool = True,
        on_icon_sync: Callable[[], None] | None = None,
    ) -> None:
        if view_id not in self._rows:
            return
        prev_id = self._active_id
        self._active_id = view_id

        for vid, row in self._rows.items():
            row.button.set_nav_active(vid == view_id)

        self._icon_sync_pending = on_icon_sync
        should_animate = animate and prev_id is not None and prev_id != view_id
        self._move_pill_to(self._rows[view_id], animate=should_animate)

    def _pill_target(self, row: NavItemRow) -> QRect:
        top_left = row.mapTo(self, row.rect().topLeft())
        return pill_geometry_for_row(QRect(top_left, row.size()))

    def _move_pill_to(self, row: NavItemRow, *, animate: bool) -> None:
        target = self._pill_target(row)
        if self._pill_anim is not None:
            self._pill_anim.stop()
            self._pill_anim.deleteLater()
            self._pill_anim = None

        if not animate or not self._pill.isVisible():
            self._pill.setGeometry(target)
            self._pill.show()
            self._pill.lower()
            self._sync_icons_now()
            return

        self._pill.show()
        self._pill.lower()
        anim = QPropertyAnimation(self._pill, b"geometry", self)
        anim.setDuration(NAV_ANIM_SELECT_MS)
        anim.setStartValue(self._pill.geometry())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self._on_pill_value_changed)
        anim.finished.connect(self._on_pill_finished)
        self._pill_anim = anim
        self._icon_synced = False
        anim.start()

    def _on_pill_value_changed(self, _value) -> None:
        if self._icon_sync_pending is None or getattr(self, "_icon_synced", True):
            return
        anim = self._pill_anim
        if anim is None or anim.duration() <= 0:
            return
        ratio = anim.currentTime() / anim.duration()
        if ratio >= NAV_ICON_SYNC_RATIO:
            self._sync_icons_now()

    def _on_pill_finished(self) -> None:
        self._sync_icons_now()
        if self._pill_anim is not None:
            self._pill_anim.deleteLater()
            self._pill_anim = None

    def _sync_icons_now(self) -> None:
        if self._icon_sync_pending is None:
            return
        self._icon_synced = True
        self._icon_sync_pending()
        self._icon_sync_pending = None

    def sync_pill_geometry(self, *, animate: bool = False) -> None:
        if self._active_id is None:
            return
        row = self._rows.get(self._active_id)
        if row is None:
            return
        self._move_pill_to(row, animate=animate)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self._initial_pill_placement)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        QTimer.singleShot(0, lambda: self.sync_pill_geometry(animate=False))

    def _initial_pill_placement(self) -> None:
        if self._active_id is None:
            return
        row = self._rows.get(self._active_id)
        if row is None:
            return
        self._pill.setGeometry(self._pill_target(row))
        self._pill.show()
        self._pill.lower()
