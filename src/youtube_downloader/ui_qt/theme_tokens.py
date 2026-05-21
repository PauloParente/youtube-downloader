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
PREVIEW_EMPTY_MIN_HEIGHT = 240
PREVIEW_EMPTY_ICON_SIZE = 56

FONT_FAMILY = '"Segoe UI Variable", "Segoe UI"'
FONT_BODY = 13
FONT_TITLE_BAR = 13
FONT_CAPTION = 11
FONT_SECTION = 13
FONT_PAGE_TITLE = 26

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

# Brand accent (GitHub-style blue)
ACCENT = "#007BFF"
ACCENT_HOVER = "#0069D9"
ACCENT_MUTED = "#1F6FEB"
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
    btn_secondary_border: str
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
    alert_info_bg: str
    alert_info_border: str
    alert_info_text: str


DARK = ThemePalette(
    app_bg="#0D1117",
    card_bg="#161B22",
    card_border="#30363D",
    input_bg="#0D1117",
    input_border="#30363D",
    text_primary="#FFFFFF",
    text_secondary="#8B949E",
    text_muted="#6E7681",
    btn_secondary="#21262D",
    btn_secondary_hover="#30363D",
    btn_secondary_border="#30363D",
    btn_disabled="#21262D",
    sidebar_bg="#161B22",
    sidebar_active_bg="#1C2128",
    accent_subtle="#111D2C",
    progress_track="#30363D",
    surface_elevated="#21262D",
    overlay_badge_bg="#000000",
    overlay_badge_text="#FFFFFF",
    scrollbar_bg="#161B22",
    scrollbar_handle="#484F58",
    focus_border=ACCENT,
    link_color="#58A6FF",
    divider="#30363D",
    alert_info_bg="#111D2C",
    alert_info_border="#1F6FEB",
    alert_info_text="#58A6FF",
)

LIGHT = ThemePalette(
    app_bg="#F6F8FA",
    card_bg="#FFFFFF",
    card_border="#D0D7DE",
    input_bg="#FFFFFF",
    input_border="#D0D7DE",
    text_primary="#1F2328",
    text_secondary="#656D76",
    text_muted="#8C959F",
    btn_secondary="#F6F8FA",
    btn_secondary_hover="#EAEEF2",
    btn_secondary_border="#D0D7DE",
    btn_disabled="#EAEEF2",
    sidebar_bg="#F6F8FA",
    sidebar_active_bg="#DDF4FF",
    accent_subtle="#DDF4FF",
    progress_track="#D0D7DE",
    surface_elevated="#F6F8FA",
    overlay_badge_bg="#1F2328",
    overlay_badge_text="#FFFFFF",
    scrollbar_bg="#F6F8FA",
    scrollbar_handle="#C0C0C0",
    focus_border=ACCENT,
    link_color="#0969DA",
    divider="#D0D7DE",
    alert_info_bg="#DDF4FF",
    alert_info_border="#54AEFF",
    alert_info_text="#0969DA",
)
