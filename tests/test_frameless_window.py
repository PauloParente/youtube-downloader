"""Frameless resize hit-test."""

from PySide6.QtCore import QRect

from youtube_downloader.ui_qt.frameless_window import (
    HT_RIGHT,
    HT_TOP_LEFT,
    ResizeEdge,
    hit_test_frame_edges,
    resize_edge_to_ht,
)


def test_hit_test_left_edge() -> None:
    frame = QRect(100, 100, 800, 600)
    edge = hit_test_frame_edges(frame, 102, 400)
    assert edge == ResizeEdge.LEFT


def test_hit_test_top_left_corner() -> None:
    frame = QRect(0, 0, 400, 300)
    edge = hit_test_frame_edges(frame, 3, 3)
    assert edge == (ResizeEdge.LEFT | ResizeEdge.TOP)
    assert resize_edge_to_ht(edge) == HT_TOP_LEFT


def test_hit_test_interior_none() -> None:
    frame = QRect(0, 0, 400, 300)
    edge = hit_test_frame_edges(frame, 200, 150)
    assert edge == ResizeEdge.NONE


def test_resize_edge_to_ht_right() -> None:
    assert resize_edge_to_ht(ResizeEdge.RIGHT) == HT_RIGHT
