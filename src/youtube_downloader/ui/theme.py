"""Visual theme aligned with Stitch mockups (dark utilitarian desktop)."""

# Backgrounds
APP_BG = "#121212"
CARD_BG = "#1E1E1E"
CARD_BORDER = "#2D2D2D"
INPUT_BG = "#252525"
INPUT_BORDER = "#3A3A3A"

# Text
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#A0A0A0"
TEXT_MUTED = "#6B6B6B"

# Accent (primary actions, active checkbox, links)
ACCENT = "#007BFF"
ACCENT_HOVER = "#0069D9"

# Buttons
BTN_SECONDARY = "#2D2D2D"
BTN_SECONDARY_HOVER = "#3D3D3D"
BTN_DISABLED = "#3A3A3A"

# Typography helpers (CustomTkinter font tuples)
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_SECTION = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 11)
FONT_CAPTION = ("Segoe UI", 10)

# Widget styles
PRIMARY_BTN = {
    "fg_color": ACCENT,
    "hover_color": ACCENT_HOVER,
    "text_color": TEXT_PRIMARY,
    "corner_radius": 6,
}
SECONDARY_BTN = {
    "fg_color": BTN_SECONDARY,
    "hover_color": BTN_SECONDARY_HOVER,
    "text_color": TEXT_PRIMARY,
    "corner_radius": 6,
}
OUTLINE_BTN = {
    "fg_color": "transparent",
    "border_width": 1,
    "border_color": INPUT_BORDER,
    "hover_color": BTN_SECONDARY,
    "text_color": TEXT_PRIMARY,
    "corner_radius": 6,
}
GHOST_BTN = {
    "fg_color": "transparent",
    "hover_color": BTN_SECONDARY,
    "text_color": TEXT_SECONDARY,
    "corner_radius": 4,
    "height": 28,
    "width": 36,
}
LINK_BTN = {
    "fg_color": "transparent",
    "hover_color": BTN_SECONDARY,
    "text_color": ACCENT,
    "height": 24,
    "corner_radius": 4,
}
YOUTUBE_BTN = {
    "fg_color": "#CC0000",
    "hover_color": "#FF0000",
    "text_color": "#FFFFFF",
    "corner_radius": 6,
    "width": 36,
    "height": 32,
}
MENU_BTN = {
    "fg_color": "transparent",
    "hover_color": BTN_SECONDARY,
    "text_color": TEXT_SECONDARY,
    "corner_radius": 4,
    "height": 28,
    "anchor": "w",
}

CARD_STYLE = {
    "fg_color": CARD_BG,
    "corner_radius": 8,
    "border_width": 1,
    "border_color": CARD_BORDER,
}

ENTRY_STYLE = {
    "fg_color": INPUT_BG,
    "border_color": INPUT_BORDER,
    "border_width": 1,
    "corner_radius": 6,
    "text_color": TEXT_PRIMARY,
    "placeholder_text_color": TEXT_MUTED,
}

# Shell layout (sidebar + top bar)
SIDEBAR_WIDTH = 220
SIDEBAR_BG = "#161616"
SIDEBAR_ACTIVE_BG = "#252528"
TOPBAR_HEIGHT = 52
ICON_BTN = {
    "fg_color": "transparent",
    "hover_color": BTN_SECONDARY,
    "text_color": TEXT_SECONDARY,
    "border_width": 1,
    "border_color": INPUT_BORDER,
    "corner_radius": 16,
    "width": 32,
    "height": 32,
}
NAV_BTN = {
    "fg_color": "transparent",
    "hover_color": SIDEBAR_ACTIVE_BG,
    "text_color": TEXT_SECONDARY,
    "anchor": "w",
    "height": 40,
    "corner_radius": 6,
}
