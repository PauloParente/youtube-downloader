"""Frameless window border + edge resize (Windows WM_NCHITTEST, Qt mouse fallback)."""

from __future__ import annotations

import ctypes
import sys
from ctypes import POINTER, c_int, cast
from ctypes import wintypes
from enum import IntFlag
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

# Visual border via QSS on #windowRoot (theme.py). Hit-test margin for resize.
RESIZE_HIT_MARGIN_PX = 6

HT_CLIENT = 1
HT_LEFT = 10
HT_RIGHT = 11
HT_TOP = 12
HT_TOP_LEFT = 13
HT_TOP_RIGHT = 14
HT_BOTTOM = 15
HT_BOTTOM_LEFT = 16
HT_BOTTOM_RIGHT = 17


class ResizeEdge(IntFlag):
    NONE = 0
    LEFT = 1
    TOP = 2
    RIGHT = 4
    BOTTOM = 8


def _signed_lo(value: int) -> int:
    return c_int(value & 0xFFFF).value


def _signed_hi(value: int) -> int:
    return c_int((value >> 16) & 0xFFFF).value


def hit_test_frame_edges(
    frame: QRect,
    global_x: int,
    global_y: int,
    *,
    margin: int = RESIZE_HIT_MARGIN_PX,
) -> ResizeEdge:
    """Return resize edges under (global_x, global_y), or NONE."""
    if not frame.isValid():
        return ResizeEdge.NONE
    left = frame.left() <= global_x <= frame.left() + margin - 1
    right = frame.right() - margin + 1 <= global_x <= frame.right()
    top = frame.top() <= global_y <= frame.top() + margin - 1
    bottom = frame.bottom() - margin + 1 <= global_y <= frame.bottom()
    in_x = frame.left() <= global_x <= frame.right()
    in_y = frame.top() <= global_y <= frame.bottom()

    edge = ResizeEdge.NONE
    if left and in_y:
        edge |= ResizeEdge.LEFT
    if right and in_y:
        edge |= ResizeEdge.RIGHT
    if top and in_x:
        edge |= ResizeEdge.TOP
    if bottom and in_x:
        edge |= ResizeEdge.BOTTOM
    return edge


def resize_edge_to_ht(edge: ResizeEdge) -> int:
    if edge == (ResizeEdge.LEFT | ResizeEdge.TOP):
        return HT_TOP_LEFT
    if edge == (ResizeEdge.RIGHT | ResizeEdge.TOP):
        return HT_TOP_RIGHT
    if edge == (ResizeEdge.LEFT | ResizeEdge.BOTTOM):
        return HT_BOTTOM_LEFT
    if edge == (ResizeEdge.RIGHT | ResizeEdge.BOTTOM):
        return HT_BOTTOM_RIGHT
    if edge & ResizeEdge.LEFT:
        return HT_LEFT
    if edge & ResizeEdge.RIGHT:
        return HT_RIGHT
    if edge & ResizeEdge.TOP:
        return HT_TOP
    if edge & ResizeEdge.BOTTOM:
        return HT_BOTTOM
    return HT_CLIENT


def cursor_for_resize_edge(edge: ResizeEdge):
    from PySide6.QtCore import Qt

    if edge in (
        ResizeEdge.LEFT | ResizeEdge.TOP,
        ResizeEdge.RIGHT | ResizeEdge.BOTTOM,
    ):
        return Qt.CursorShape.SizeFDiagCursor
    if edge in (
        ResizeEdge.RIGHT | ResizeEdge.TOP,
        ResizeEdge.LEFT | ResizeEdge.BOTTOM,
    ):
        return Qt.CursorShape.SizeBDiagCursor
    if edge & (ResizeEdge.LEFT | ResizeEdge.RIGHT):
        return Qt.CursorShape.SizeHorCursor
    if edge & (ResizeEdge.TOP | ResizeEdge.BOTTOM):
        return Qt.CursorShape.SizeVerCursor
    return Qt.CursorShape.ArrowCursor


def try_native_resize_event(
    window: QMainWindow,
    event_type,
    message,
) -> Optional[tuple[bool, int]]:
    """Handle WM_NCHITTEST on Windows; return (handled, result) or None."""
    if sys.platform != "win32":
        return None
    et = event_type.data().decode("ascii") if hasattr(event_type, "data") else str(event_type)
    if et != "windows_generic_MSG":
        return None
    if window.isMaximized():
        return None

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", POINT),
        ]

    msg = cast(int(message), POINTER(MSG)).contents
    if msg.message != 0x84:  # WM_NCHITTEST
        return None

    x = _signed_lo(msg.lParam)
    y = _signed_hi(msg.lParam)
    edge = hit_test_frame_edges(window.frameGeometry(), x, y)
    if edge == ResizeEdge.NONE:
        return None
    return True, resize_edge_to_ht(edge)


def apply_mouse_resize(
    window: QMainWindow,
    edge: ResizeEdge,
    start_global: QPointF,
    start_geom: QRect,
    current_global: QPointF,
    *,
    min_width: int,
    min_height: int,
) -> None:
    delta = current_global - start_global
    geo = QRect(start_geom)
    if edge & ResizeEdge.LEFT:
        geo.setLeft(geo.left() + int(delta.x()))
    if edge & ResizeEdge.RIGHT:
        geo.setRight(geo.right() + int(delta.x()))
    if edge & ResizeEdge.TOP:
        geo.setTop(geo.top() + int(delta.y()))
    if edge & ResizeEdge.BOTTOM:
        geo.setBottom(geo.bottom() + int(delta.y()))

    if geo.width() < min_width:
        if edge & ResizeEdge.LEFT:
            geo.setLeft(geo.right() - min_width + 1)
        else:
            geo.setRight(geo.left() + min_width - 1)
    if geo.height() < min_height:
        if edge & ResizeEdge.TOP:
            geo.setTop(geo.bottom() - min_height + 1)
        else:
            geo.setBottom(geo.top() + min_height - 1)
    window.setGeometry(geo)


def update_resize_cursor(window: QMainWindow, global_pos: QPointF) -> None:
    if window.isMaximized():
        window.unsetCursor()
        return
    edge = hit_test_frame_edges(
        window.frameGeometry(),
        int(global_pos.x()),
        int(global_pos.y()),
    )
    if edge == ResizeEdge.NONE:
        window.unsetCursor()
    else:
        window.setCursor(QCursor(cursor_for_resize_edge(edge)))


def setup_window_root(root: QWidget) -> None:
    root.setObjectName("windowRoot")
