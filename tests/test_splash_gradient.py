"""Tests for animated splash gradient geometry."""

from __future__ import annotations

import math

from youtube_downloader.ui_qt.splash_screen import scrolling_gradient_endpoints


def test_scrolling_gradient_endpoints_same_sign_phase_extremes_differ() -> None:
    w, h = 480, 320
    angle = math.pi / 4
    low = scrolling_gradient_endpoints(w, h, 0.0, angle, scroll_sign=1.0)
    high = scrolling_gradient_endpoints(w, h, 1.0, angle, scroll_sign=1.0)
    assert low != high


def test_scrolling_gradient_scroll_sign_reverses_drift() -> None:
    w, h = 400, 300
    angle = math.pi / 6
    forward = scrolling_gradient_endpoints(w, h, 0.4, angle, scroll_sign=1.0)
    backward = scrolling_gradient_endpoints(w, h, 0.4, angle, scroll_sign=-1.0)
    assert forward != backward


def test_scrolling_gradient_endpoints_angle_changes_line() -> None:
    w, h = 400, 300
    horizontal = scrolling_gradient_endpoints(w, h, 0.25, 0.0)
    vertical = scrolling_gradient_endpoints(w, h, 0.25, math.pi / 2)
    assert horizontal != vertical


def test_scrolling_gradient_phase_shifts_endpoints() -> None:
    w, h = 500, 280
    angle = math.pi / 3
    early = scrolling_gradient_endpoints(w, h, 0.1, angle, scroll_sign=1.0)
    late = scrolling_gradient_endpoints(w, h, 0.6, angle, scroll_sign=1.0)
    assert early != late
