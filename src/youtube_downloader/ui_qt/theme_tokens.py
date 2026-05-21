"""Design tokens — single source for colors, spacing, and typography."""

from __future__ import annotations

from dataclasses import dataclass

# Spacing (8px grid)
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32

PAGE_MARGINS = (SPACE_LG, 20, SPACE_LG, 20)
CARD_PADDING = SPACE_MD
SIDEBAR_WIDTH = 220
TITLE_BAR_HEIGHT = 50
TITLE_BAR_ICON_SIZE = 12

RADIUS_CARD = 10
RADIUS_INPUT = 8
RADIUS_BUTTON = 8
RADIUS_THUMB = 8

# Hero inputs (URL Downloads, filtros Histórico/Biblioteca) e controlos na mesma linha
INPUT_HERO_HEIGHT = 44

FONT_FAMILY = '"Segoe UI Variable", "Segoe UI"'
FONT_BODY = 13
FONT_TITLE_BAR = 13
FONT_CAPTION = 11
FONT_SECTION = 13
FONT_PAGE_TITLE = 22

# Sidebar nav animations (ms)
NAV_ANIM_HOVER_IN_MS = 140
NAV_ANIM_HOVER_OUT_MS = 100
NAV_ANIM_HOVER_ACTIVE_MS = 120
NAV_ANIM_PRESS_IN_MS = 80
NAV_ANIM_PRESS_OUT_MS = 120
NAV_ANIM_SELECT_MS = 200
NAV_ICON_SYNC_RATIO = 0.7
NAV_ITEM_HEIGHT = 40
NAV_BADGE_SLOT_WIDTH = 28

# Brand accent
ACCENT = "#5B8DEF"
ACCENT_HOVER = "#4A7AD9"
ACCENT_MUTED = "#3D5A99"
DANGER = "#DC3545"
DANGER_HOVER = "#C82333"
SUCCESS = "#28A745"
WARNING = "#FFC107"


@dataclass(frozen=True)
class ThemePalette:
    app_bg: str
    card_bg: str
    card_border: str
    input_bg: str
    input_border: str
    text_primary: str
    text_secondary: str
    text_muted: str
    btn_secondary: str
    btn_secondary_hover: str
    btn_disabled: str
    sidebar_bg: str
    sidebar_active_bg: str
    accent_subtle: str
    progress_track: str
    surface_elevated: str
    overlay_badge_bg: str
    overlay_badge_text: str
    scrollbar_bg: str
    scrollbar_handle: str
    focus_border: str
    link_color: str
    divider: str


DARK = ThemePalette(
    app_bg="#0F0F0F",
    card_bg="#1A1A1A",
    card_border="#2A2A2A",
    input_bg="#222222",
    input_border="#383838",
    text_primary="#F0F0F0",
    text_secondary="#A8A8A8",
    text_muted="#6E6E6E",
    btn_secondary="#262626",
    btn_secondary_hover="#333333",
    btn_disabled="#2E2E2E",
    sidebar_bg="#141414",
    sidebar_active_bg="#1E2433",
    accent_subtle="#1A2744",
    progress_track="#2A2A2A",
    surface_elevated="#242424",
    overlay_badge_bg="#000000",
    overlay_badge_text="#FFFFFF",
    scrollbar_bg="#141414",
    scrollbar_handle="#3A3A3A",
    focus_border=ACCENT,
    link_color=ACCENT,
    divider="#252525",
)

LIGHT = ThemePalette(
    app_bg="#F3F4F6",
    card_bg="#FFFFFF",
    card_border="#E2E4E8",
    input_bg="#FFFFFF",
    input_border="#D0D4DA",
    text_primary="#141414",
    text_secondary="#5C5C5C",
    text_muted="#757575",
    btn_secondary="#ECEEF2",
    btn_secondary_hover="#DDE0E6",
    btn_disabled="#E8E8E8",
    sidebar_bg="#EBEDF0",
    sidebar_active_bg="#E0E8F8",
    accent_subtle="#E8EEFC",
    progress_track="#E0E0E0",
    surface_elevated="#F5F6F8",
    overlay_badge_bg="#1A1A1A",
    overlay_badge_text="#FFFFFF",
    scrollbar_bg="#F0F0F0",
    scrollbar_handle="#C0C0C0",
    focus_border=ACCENT,
    link_color=ACCENT,
    divider="#D8DCE2",
)
