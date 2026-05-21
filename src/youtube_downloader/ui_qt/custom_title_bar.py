"""Frameless window title bar aligned with sidebar brand column."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QWidget,
)

from youtube_downloader.config import APP_TITLE
from youtube_downloader.ui_qt.icons import accent_icon, themed_icon
from youtube_downloader.ui_qt.theme_tokens import (
    DARK,
    LIGHT,
    SIDEBAR_WIDTH,
    TITLE_BAR_HEIGHT,
    TITLE_BAR_ICON_SIZE,
    ThemePalette,
)

_CLOSE_HOVER_ICON = "#FFFFFF"


class CustomTitleBar(QFrame):
    """Brand column (sidebar width) + drag region + window controls."""

    def __init__(self, window: QMainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("customTitleBar")
        self.setFixedHeight(TITLE_BAR_HEIGHT)
        self._window = window
        self._drag_origin: Optional[QPoint] = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        brand = QWidget()
        brand.setObjectName("titleBarBrand")
        brand.setFixedWidth(SIDEBAR_WIDTH)
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(14, 0, 14, 0)
        brand_layout.setSpacing(10)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon = QLabel()
        icon.setObjectName("brandIcon")
        icon.setFixedSize(36, 36)
        icon.setAutoFillBackground(False)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(accent_icon("play", 20).pixmap(20, 20))
        brand_layout.addWidget(icon)

        title_lbl = QLabel(APP_TITLE)
        title_lbl.setObjectName("titleBarTitle")
        title_lbl.setTextFormat(Qt.TextFormat.PlainText)
        title_lbl.setAutoFillBackground(False)
        brand_layout.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addStretch()
        root.addWidget(brand)

        self._drag_region = QWidget()
        self._drag_region.setObjectName("titleBarDrag")
        root.addWidget(self._drag_region, stretch=1)

        controls = QWidget()
        controls.setObjectName("titleBarControls")
        controls.setAutoFillBackground(False)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 8, 0)
        controls_layout.setSpacing(0)

        icon_size = QSize(TITLE_BAR_ICON_SIZE, TITLE_BAR_ICON_SIZE)

        self._min_btn = QPushButton()
        self._min_btn.setObjectName("titleBarButton")
        self._min_btn.setToolTip("Minimizar")
        self._min_btn.setIconSize(icon_size)
        self._min_btn.clicked.connect(window.showMinimized)
        controls_layout.addWidget(self._min_btn)

        self._max_btn = QPushButton()
        self._max_btn.setObjectName("titleBarButton")
        self._max_btn.setToolTip("Maximizar")
        self._max_btn.setIconSize(icon_size)
        self._max_btn.clicked.connect(self._toggle_maximize)
        controls_layout.addWidget(self._max_btn)

        self._close_btn = QPushButton()
        self._close_btn.setObjectName("titleBarButtonClose")
        self._close_btn.setToolTip("Fechar")
        self._close_btn.setIconSize(icon_size)
        self._close_btn.clicked.connect(window.close)
        self._close_btn.installEventFilter(self)
        controls_layout.addWidget(self._close_btn)

        root.addWidget(controls)
        self.refresh_control_icons()

    @staticmethod
    def _active_palette() -> ThemePalette:
        app = QApplication.instance()
        sheet = app.styleSheet() if app is not None else ""
        return LIGHT if LIGHT.app_bg in sheet else DARK

    def _set_control_icon(self, button: QPushButton, name: str, color: str) -> None:
        button.setIcon(themed_icon(name, TITLE_BAR_ICON_SIZE, color=color))

    def refresh_control_icons(self) -> None:
        """Re-tint window controls after theme change."""
        palette = self._active_palette()
        self._set_control_icon(self._min_btn, "minimize", palette.text_secondary)
        max_name = "restore" if self._window.isMaximized() else "maximize"
        self._set_control_icon(self._max_btn, max_name, palette.text_secondary)
        self._set_control_icon(self._close_btn, "close", palette.text_secondary)

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def sync_maximize_button(self) -> None:
        palette = self._active_palette()
        max_name = "restore" if self._window.isMaximized() else "maximize"
        self._set_control_icon(self._max_btn, max_name, palette.text_secondary)
        tip = "Restaurar" if self._window.isMaximized() else "Maximizar"
        self._max_btn.setToolTip(tip)

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        if watched is self._close_btn:
            if event.type() == QEvent.Type.Enter:
                self._set_control_icon(self._close_btn, "close", _CLOSE_HOVER_ICON)
            elif event.type() == QEvent.Type.Leave:
                self._set_control_icon(
                    self._close_btn,
                    "close",
                    self._active_palette().text_secondary,
                )
        return super().eventFilter(watched, event)

    def _global_pos(self, event: QMouseEvent) -> QPoint:
        return event.globalPosition().toPoint()

    def _start_drag(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._window.isMaximized():
            return
        self._drag_origin = self._global_pos(event) - self._window.frameGeometry().topLeft()

    def _move_drag(self, event: QMouseEvent) -> None:
        if self._drag_origin is None:
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            self._drag_origin = None
            return
        self._window.move(self._global_pos(event) - self._drag_origin)

    def _end_drag(self) -> None:
        self._drag_origin = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._start_drag(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._move_drag(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._end_drag()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
        super().mouseDoubleClickEvent(event)
