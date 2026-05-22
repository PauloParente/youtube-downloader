"""Tests for display-synced animation timing helpers."""

from __future__ import annotations

import math

import pytest

from youtube_downloader.ui_qt.animation_timing import (
    angle_step_toward,
    exponential_step,
    pulse_opacity,
    repaint_interval_ms,
)


def test_exponential_step_converges_toward_target() -> None:
    value = 0.0
    for _ in range(200):
        value = exponential_step(value, 1.0, 1.0 / 60.0, response_sec=0.2)
    assert value == pytest.approx(1.0, abs=0.02)


def test_exponential_step_similar_after_same_wall_time() -> None:
    """60 Hz vs 120 Hz integration should match within tolerance."""

    def integrate(hz: float) -> float:
        value = 0.0
        dt = 1.0 / hz
        steps = int(1.0 * hz)
        for _ in range(steps):
            value = exponential_step(value, 1.0, dt, response_sec=0.5)
        return value

    assert integrate(60.0) == pytest.approx(integrate(120.0), abs=0.03)


def test_angle_step_toward_shortest_path() -> None:
    start = 0.1
    target = math.pi - 0.1
    next_angle = angle_step_toward(start, target, 0.016, response_sec=1.0)
    assert next_angle > start


def test_repaint_interval_ms_scales_with_hz() -> None:
    assert repaint_interval_ms(screen_hz=60.0) == 17
    assert repaint_interval_ms(screen_hz=120.0) == 8
    assert repaint_interval_ms(screen_hz=30.0) == 33


def test_pulse_opacity_within_bounds() -> None:
    for ms in range(0, 2000, 17):
        value = pulse_opacity(float(ms), 1800.0, 0.35, 0.65)
        assert 0.35 <= value <= 0.65
