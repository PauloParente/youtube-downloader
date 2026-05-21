"""Single source of truth for sidebar nav items and stack order."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    view_id: str
    icon: str
    label: str
    shortcut: str | None = None


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("download", "download", "Downloads", "Ctrl+1"),
    NavItem("queue", "queue", "Fila", "Ctrl+2"),
    NavItem("library", "library", "Biblioteca", "Ctrl+3"),
    NavItem("history", "history", "Histórico", "Ctrl+4"),
    NavItem("settings", "settings", "Configurações", "Ctrl+5"),
)

DEFAULT_VIEW_ID = NAV_ITEMS[0].view_id


def view_ids() -> tuple[str, ...]:
    return tuple(item.view_id for item in NAV_ITEMS)


def stack_index(view_id: str) -> int | None:
    for index, item in enumerate(NAV_ITEMS):
        if item.view_id == view_id:
            return index
    return None


def nav_item(view_id: str) -> NavItem | None:
    for item in NAV_ITEMS:
        if item.view_id == view_id:
            return item
    return None
