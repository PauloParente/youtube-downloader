"""Splash screen during startup."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from youtube_downloader.config import APP_TITLE, APP_VERSION, SPLASH_LOGO_PATH, SPLASH_SIZE
from youtube_downloader.ui_qt.theme_tokens import (
    ACCENT_MUTED,
    DARK,
    FONT_CAPTION,
    FONT_PAGE_TITLE,
    LIGHT,
    ThemePalette,
)
from youtube_downloader.ui_qt.widgets import secondary_label

if TYPE_CHECKING:
    pass

# Animated gradient
_SPLASH_ANIM_MS = 33
_SPLASH_PHASE_STEP_BASE = 0.0015
_SPLASH_SPEED_MIN = 0.4
_SPLASH_SPEED_MAX = 1.0
_SPLASH_SPEED_CHANGE_SEC = 3.0
_SPLASH_SPEED_LERP = 0.035
_SPLASH_DIRECTION_CHANGE_SEC = 9.0
_SPLASH_ANGLE_LERP = 0.007

# Wider soft bands between stops (0–1); longer line = broader blends on screen
_SPLASH_GRADIENT_STOP_POS = (0.0, 0.26, 0.74, 1.0)
_SPLASH_GRADIENT_LENGTH_SCALE = 1.2

# Dark splash: lifted charcoal instead of near-black app_bg (#0F0F0F)
_SPLASH_DARK_SOFT = "#1C1D26"


def parse_window_size(size: str) -> tuple[int, int]:
    parts = size.lower().split("x", 1)
    return int(parts[0]), int(parts[1])


def center_on_screen(widget: QWidget) -> None:
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    x = geo.x() + (geo.width() - widget.width()) // 2
    y = geo.y() + (geo.height() - widget.height()) // 2
    widget.move(x, y)


def _palette_for_mode(appearance_mode: str) -> ThemePalette:
    return LIGHT if appearance_mode == "light" else DARK


def scrolling_gradient_endpoints(
    width: int,
    height: int,
    phase: float,
    angle_rad: float,
    *,
    scroll_sign: float = 1.0,
) -> tuple[float, float, float, float]:
    """Linear gradient line; ``phase`` in [0, 1], ``scroll_sign`` ±1 sets drift direction."""
    w = max(float(width), 1.0)
    h = max(float(height), 1.0)
    phase_clamped = min(1.0, max(0.0, phase))
    sign = -1.0 if scroll_sign < 0 else 1.0
    length = math.hypot(w, h) * _SPLASH_GRADIENT_LENGTH_SCALE
    cx, cy = w * 0.5, h * 0.5
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    scroll = phase_clamped * length * 2.0 * sign
    ox = cos_a * scroll
    oy = sin_a * scroll
    x1 = cx - cos_a * length + ox
    y1 = cy - sin_a * length + oy
    x2 = cx + cos_a * length + ox
    y2 = cy + sin_a * length + oy
    return x1, y1, x2, y2


def _content_stylesheet(p: ThemePalette) -> str:
    return f"""
        QLabel {{
            background: transparent;
        }}
        QLabel#pageTitle {{
            font-size: {FONT_PAGE_TITLE}px;
            font-weight: 600;
            color: {p.text_primary};
        }}
        QLabel[class="secondary"] {{
            color: {p.text_secondary};
            font-size: {FONT_CAPTION}px;
        }}
    """


def _hex_color(value: str) -> QColor:
    c = QColor(value)
    if not c.isValid():
        c = QColor("#000000")
    return c


def _splash_gradient_colors(
    appearance_mode: str, p: ThemePalette
) -> tuple[str, str, str, str]:
    """Four stops from dark to accent; wider spacing applied in paint."""
    if appearance_mode == "light":
        return (
            p.app_bg,
            p.sidebar_bg,
            p.accent_subtle,
            ACCENT_MUTED,
        )
    return (
        _SPLASH_DARK_SOFT,
        p.card_bg,
        p.accent_subtle,
        ACCENT_MUTED,
    )


def _apply_splash_gradient_stops(
    grad: QLinearGradient,
    colors: tuple[str, str, str, str],
    *,
    reverse: bool,
) -> None:
    ordered = tuple(reversed(colors)) if reverse else colors
    for pos, hex_color in zip(_SPLASH_GRADIENT_STOP_POS, ordered, strict=True):
        grad.setColorAt(pos, _hex_color(hex_color))


class AnimatedSplashWidget(QWidget):
    """Frameless splash with a slowly scrolling linear gradient background."""

    def __init__(self, width: int, height: int, appearance_mode: str = "dark") -> None:
        super().__init__()
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._appearance_mode = appearance_mode
        self._palette = _palette_for_mode(appearance_mode)
        self._phase = random.random()
        self._scroll_sign = random.choice([-1.0, 1.0])
        self._reverse_stops = random.choice([False, True])
        self._angle = random.uniform(0.0, 2.0 * math.pi)
        self._target_angle = self._angle
        self._direction_timer_sec = 0.0
        self._speed_factor = random.uniform(_SPLASH_SPEED_MIN, _SPLASH_SPEED_MAX)
        self._target_speed = self._speed_factor
        self._speed_timer_sec = 0.0

        self.setStyleSheet(_content_stylesheet(self._palette))
        self._build_content()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(_SPLASH_ANIM_MS)

    def _build_content(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if SPLASH_LOGO_PATH.is_file():
            try:
                logo = QPixmap(str(SPLASH_LOGO_PATH)).scaled(
                    48, 48, Qt.AspectRatioMode.KeepAspectRatio
                )
                logo_lbl = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
                logo_lbl.setPixmap(logo)
                layout.addWidget(logo_lbl)
            except Exception:
                pass
        title = QLabel(f"<b>{APP_TITLE}</b> v{APP_VERSION}")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(secondary_label("A carregar. Por favor, aguarde…"))

    def _pick_new_direction(self) -> None:
        presets = (
            0.0,
            math.pi / 4,
            math.pi / 2,
            3 * math.pi / 4,
            math.pi,
            -math.pi / 4,
        )
        if random.random() < 0.35:
            self._target_angle = random.uniform(0.0, 2.0 * math.pi)
        else:
            self._target_angle = random.choice(presets) + random.uniform(
                -0.12, 0.12
            )
        self._scroll_sign = random.choice([-1.0, 1.0])
        self._reverse_stops = random.choice([False, True])
        self._pick_new_scroll_speed()

    def _pick_new_scroll_speed(self) -> None:
        self._target_speed = random.uniform(_SPLASH_SPEED_MIN, _SPLASH_SPEED_MAX)

    def _on_tick(self) -> None:
        dt = _SPLASH_ANIM_MS / 1000.0
        self._speed_timer_sec += dt
        if self._speed_timer_sec >= _SPLASH_SPEED_CHANGE_SEC:
            self._speed_timer_sec = 0.0
            self._pick_new_scroll_speed()
        self._speed_factor += (self._target_speed - self._speed_factor) * _SPLASH_SPEED_LERP

        step = _SPLASH_PHASE_STEP_BASE * self._speed_factor
        self._phase += step * self._scroll_sign
        if self._phase >= 1.0:
            self._phase = 1.0 - (self._phase - 1.0)
            self._scroll_sign = -1.0
        elif self._phase <= 0.0:
            self._phase = -self._phase
            self._scroll_sign = 1.0
        self._direction_timer_sec += dt
        if self._direction_timer_sec >= _SPLASH_DIRECTION_CHANGE_SEC:
            self._direction_timer_sec = 0.0
            self._pick_new_direction()

        delta = self._target_angle - self._angle
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        self._angle += delta * _SPLASH_ANGLE_LERP
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        p = self._palette
        x1, y1, x2, y2 = scrolling_gradient_endpoints(
            self.width(),
            self.height(),
            self._phase,
            self._angle,
            scroll_sign=self._scroll_sign,
        )
        grad = QLinearGradient(x1, y1, x2, y2)
        colors = _splash_gradient_colors(self._appearance_mode, p)
        _apply_splash_gradient_stops(
            grad, colors, reverse=self._reverse_stops
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), grad)
        painter.end()

    def stop_animation(self) -> None:
        self._timer.stop()


class SplashScreen:
    """Frameless splash shown while the main window loads."""

    def __init__(self, appearance_mode: str = "dark") -> None:
        self._width, self._height = parse_window_size(SPLASH_SIZE)
        self._appearance_mode = appearance_mode
        self._widget: AnimatedSplashWidget | None = None

    def show(self) -> None:
        self._widget = AnimatedSplashWidget(
            self._width, self._height, self._appearance_mode
        )
        self._widget.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
        )
        self._widget.show()
        center_on_screen(self._widget)

    def finish(self, _main_window: QWidget) -> None:
        if self._widget is not None:
            self._widget.stop_animation()
            self._widget.close()
            self._widget = None

    def close(self) -> None:
        if self._widget is not None:
            self._widget.stop_animation()
            self._widget.close()
            self._widget = None
