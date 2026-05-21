"""Pure helpers for sidebar nav animation (testable without widgets)."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF


def lerp_int(a: int, b: int, t: float) -> int:
    t = max(0.0, min(1.0, t))
    return int(round(a + (b - a) * t))


def lerp_hex_color(c1: str, c2: str, t: float) -> str:
    """Linear blend between two #RRGGBB colors."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return (
        f"#{lerp_int(r1, r2, t):02x}{lerp_int(g1, g2, t):02x}{lerp_int(b1, b2, t):02x}"
    )


def pill_geometry_for_row(row_rect: QRect, *, inset_x: int = 0) -> QRect:
    """Target QRect for the sliding pill inside the nav list container."""
    return QRect(inset_x, row_rect.y(), row_rect.width() - inset_x * 2, row_rect.height())


def nav_row_highlight_rectf(width: int, height: int) -> QRectF:
    """Rounded highlight bounds for a nav row (pill and hover use the same area)."""
    return QRectF(0, 0, width, height).adjusted(1, 1, -1, -1)
