"""Display-aware, time-based animation helpers (no fixed 60 Hz cadence)."""

from __future__ import annotations

import math

from PySide6.QtCore import QElapsedTimer
from PySide6.QtWidgets import QApplication

# Used only when refresh rate is unknown (headless tests, no screen).
_FALLBACK_REFRESH_HZ = 60.0
_MIN_REFRESH_HZ = 30.0
_MAX_REFRESH_HZ = 240.0
_MIN_REPAINT_INTERVAL_MS = 4
_MAX_REPAINT_INTERVAL_MS = 50


def clamp_dt_seconds(dt_sec: float, *, max_dt_sec: float = 0.1) -> float:
    """Avoid huge jumps after pauses or debugger breaks."""
    if dt_sec <= 0.0:
        return 0.0
    return min(dt_sec, max_dt_sec)


def elapsed_seconds(timer: QElapsedTimer) -> float:
    if not timer.isValid():
        return 0.0
    return timer.elapsed() / 1000.0


def exponential_step(
    current: float,
    target: float,
    dt_sec: float,
    response_sec: float,
) -> float:
    """Frame-rate independent approach to ``target`` (time constant ``response_sec``)."""
    dt_sec = clamp_dt_seconds(dt_sec)
    if dt_sec <= 0.0 or response_sec <= 0.0:
        return current
    alpha = 1.0 - math.exp(-dt_sec / response_sec)
    return current + (target - current) * alpha


def angle_step_toward(
    angle_rad: float,
    target_rad: float,
    dt_sec: float,
    response_sec: float,
) -> float:
    """Shortest-path blend between angles in radians."""
    delta = target_rad - angle_rad
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta < -math.pi:
        delta += 2.0 * math.pi
    if dt_sec <= 0.0 or response_sec <= 0.0:
        return angle_rad
    alpha = 1.0 - math.exp(-clamp_dt_seconds(dt_sec) / response_sec)
    return angle_rad + delta * alpha


def pulse_opacity(
    elapsed_ms: float,
    period_ms: float,
    low: float,
    high: float,
) -> float:
    """Smooth opacity pulse between ``low`` and ``high`` over ``period_ms``."""
    if period_ms <= 0:
        return low
    phase = (elapsed_ms % period_ms) / period_ms
    mid = (low + high) * 0.5
    amp = (high - low) * 0.5
    return mid + amp * math.sin(2.0 * math.pi * phase - math.pi / 2.0)


def repaint_interval_ms(*, screen_hz: float | None = None) -> int:
    """Timer interval aligned with the display refresh rate (not a fixed 60 Hz)."""
    hz = screen_hz if screen_hz is not None else _detect_screen_refresh_hz()
    hz = max(_MIN_REFRESH_HZ, min(_MAX_REFRESH_HZ, hz))
    interval = int(round(1000.0 / hz))
    return max(_MIN_REPAINT_INTERVAL_MS, min(_MAX_REPAINT_INTERVAL_MS, interval))


def _detect_screen_refresh_hz() -> float:
    app = QApplication.instance()
    if app is None:
        return _FALLBACK_REFRESH_HZ
    screen = app.primaryScreen()
    if screen is None:
        return _FALLBACK_REFRESH_HZ
    hz = float(screen.refreshRate())
    if hz <= 0.0:
        return _FALLBACK_REFRESH_HZ
    return hz
