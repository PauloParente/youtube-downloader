from youtube_downloader.core.layout_utils import clamp_wraplength


def test_clamp_wraplength_within_bounds() -> None:
    assert clamp_wraplength(800) == 640
    assert clamp_wraplength(400) == 360
    assert clamp_wraplength(100) == 200


def test_clamp_wraplength_invalid_width() -> None:
    assert clamp_wraplength(0) == 640
    assert clamp_wraplength(-10) == 640
