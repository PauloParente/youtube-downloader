"""Layout helpers (toolkit-agnostic)."""


def clamp_wraplength(
    width: int,
    *,
    fraction: float = 0.9,
    min_px: int = 200,
    max_px: int = 640,
) -> int:
    """Map widget width to a safe label wrap length."""
    if width <= 1:
        return max_px
    return max(min_px, min(max_px, int(width * fraction)))
