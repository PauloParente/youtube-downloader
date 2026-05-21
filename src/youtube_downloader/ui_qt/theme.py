"""Visual theme (colors + QSS) — tokens in theme_tokens.py."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from youtube_downloader.ui_qt.theme_tokens import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_MUTED,
    DANGER,
    DANGER_HOVER,
    DARK,
    FONT_BODY,
    FONT_CAPTION,
    FONT_FAMILY,
    FONT_PAGE_TITLE,
    FONT_SECTION,
    FONT_TITLE_BAR,
    LIGHT,
    RADIUS_BUTTON,
    RADIUS_CARD,
    INPUT_HERO_HEIGHT,
    RADIUS_INPUT,
    RADIUS_THUMB,
    SIDEBAR_WIDTH,
    ThemePalette,
)

# Backward-compatible exports (dark palette)
APP_BG = DARK.app_bg
CARD_BG = DARK.card_bg
CARD_BORDER = DARK.card_border
INPUT_BG = DARK.input_bg
INPUT_BORDER = DARK.input_border
TEXT_PRIMARY = DARK.text_primary
TEXT_SECONDARY = DARK.text_secondary
TEXT_MUTED = DARK.text_muted
BTN_SECONDARY = DARK.btn_secondary
BTN_SECONDARY_HOVER = DARK.btn_secondary_hover
BTN_DISABLED = DARK.btn_disabled
SIDEBAR_BG = DARK.sidebar_bg
SIDEBAR_ACTIVE_BG = DARK.sidebar_active_bg
SURFACE_ELEVATED = DARK.surface_elevated


def _shared_qss(p: ThemePalette) -> str:
    return f"""
QFrame#card {{
    background-color: {p.card_bg};
    border: 1px solid {p.card_border};
    border-radius: {RADIUS_CARD}px;
}}
QFrame#card QLabel {{
    background-color: transparent;
}}
QFrame#card QLabel[class="fieldLabel"] {{
    background-color: transparent;
}}
QFrame#card QWidget#previewOptionsHost,
QFrame#card QWidget#downloadOptionsBar,
QFrame#card QWidget#segmentedControl {{
    background-color: transparent;
}}
QFrame#thumb, QLabel#thumb {{
    background-color: {p.surface_elevated};
    border-radius: {RADIUS_THUMB}px;
}}
QLabel#brandIcon {{
    background-color: {p.sidebar_bg};
    border-radius: {RADIUS_BUTTON}px;
}}
QWidget#windowRoot {{
    background-color: {p.app_bg};
    border: 1px solid {p.card_border};
}}
QFrame#customTitleBar {{
    background-color: {p.sidebar_bg};
    border: none;
}}
QFrame#titleBarDivider {{
    background-color: {p.divider};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
QWidget#titleBarBrand {{
    background-color: {p.sidebar_bg};
}}
QWidget#titleBarBrand QLabel {{
    background-color: transparent;
}}
QLabel#titleBarTitle {{
    color: {p.text_primary};
    font-size: {FONT_TITLE_BAR}px;
    font-weight: 600;
}}
QFrame#sidebar QLabel {{
    background-color: transparent;
}}
QWidget#titleBarDrag {{
    background-color: {p.sidebar_bg};
}}
QWidget#titleBarControls {{
    background-color: {p.sidebar_bg};
}}
QFrame#customTitleBar QPushButton#titleBarButton,
QFrame#customTitleBar QPushButton#titleBarButtonClose {{
    background-color: transparent;
    border: none;
    border-radius: {RADIUS_BUTTON}px;
    min-width: 40px;
    max-width: 40px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
}}
QFrame#customTitleBar QPushButton#titleBarButton:hover {{
    background-color: {p.btn_secondary_hover};
}}
QFrame#customTitleBar QPushButton#titleBarButton:pressed {{
    background-color: {p.btn_secondary};
}}
QFrame#customTitleBar QPushButton#titleBarButtonClose:hover {{
    background-color: {DANGER};
}}
QFrame#customTitleBar QPushButton#titleBarButtonClose:pressed {{
    background-color: {DANGER_HOVER};
}}
QFrame#sidebarDivider {{
    background-color: {p.divider};
    border: none;
    max-width: 1px;
    min-width: 1px;
}}
QFrame#surfaceInset {{
    background-color: {p.surface_elevated};
    border: none;
    border-radius: {RADIUS_INPUT}px;
}}
QPlainTextEdit#logInset {{
    background-color: {p.surface_elevated};
    border: none;
    border-radius: {RADIUS_INPUT}px;
    padding: 8px;
    font-family: Consolas, "Cascadia Mono", monospace;
}}
QLineEdit#urlHero, QLineEdit#filterInput {{
    min-height: {INPUT_HERO_HEIGHT}px;
    padding: 10px 12px 10px 12px;
    font-size: 14px;
}}
QLineEdit#urlHero {{
    padding-left: 36px;
}}
QFrame#urlToolRow {{
    background: transparent;
    border: none;
}}
QFrame#urlToolRow QPushButton {{
    min-height: {INPUT_HERO_HEIGHT}px;
}}
QFrame#urlToolRow QPushButton#iconOnly {{
    min-width: {INPUT_HERO_HEIGHT}px;
    max-width: {INPUT_HERO_HEIGHT}px;
    min-height: {INPUT_HERO_HEIGHT}px;
    max-height: {INPUT_HERO_HEIGHT}px;
    padding: 0;
}}
QFrame#urlToolRow QPushButton#link {{
    min-height: {INPUT_HERO_HEIGHT}px;
    padding: 8px 12px;
}}
QFrame#urlToolRow QLabel#urlValidIcon, QFrame#urlToolRow QLabel#urlInvalidIcon {{
    min-height: {INPUT_HERO_HEIGHT}px;
    max-height: {INPUT_HERO_HEIGHT}px;
}}
QFrame#statusBanner {{
    background-color: {p.accent_subtle};
    border: 1px solid {ACCENT_MUTED};
    border-radius: {RADIUS_INPUT}px;
    padding: 8px 12px;
}}
QFrame#statusBanner QLabel {{
    background-color: transparent;
    color: {p.text_primary};
}}
QFrame#statusBanner QPushButton#statusBannerClose {{
    background-color: transparent;
    border: none;
    border-radius: {RADIUS_BUTTON}px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
}}
QFrame#statusBanner QPushButton#statusBannerClose:hover {{
    background-color: {p.sidebar_active_bg};
}}
QFrame#downloadAlert {{
    background-color: rgba(220, 53, 69, 0.12);
    border: 1px solid {DANGER};
    border-radius: {RADIUS_INPUT}px;
}}
QFrame#downloadAlert QLabel {{
    color: {p.text_primary};
}}
QLabel#destinationChip {{
    color: {p.text_secondary};
    padding: 4px 8px;
    border-radius: {RADIUS_BUTTON}px;
    background-color: {p.btn_secondary};
}}
QLabel#destinationChip:hover {{
    background-color: {p.btn_secondary_hover};
    color: {p.text_primary};
}}
QLabel#urlValidIcon, QLabel#urlInvalidIcon {{
    min-width: 20px;
    max-width: 20px;
}}
QFrame#progressStrip {{
    background: transparent;
    border: none;
}}
QFrame#skeletonLine {{
    background-color: {p.btn_secondary};
    border-radius: 4px;
    max-height: 10px;
}}
QFrame#actionDock {{
    background-color: {p.app_bg};
    border-top: 1px solid {p.divider};
}}
QPushButton#segment {{
    background-color: {p.btn_secondary};
    color: {p.text_secondary};
    padding: 6px 16px;
    min-height: 28px;
}}
QPushButton#segment:checked {{
    background-color: {ACCENT};
    color: #FFFFFF;
}}
QPushButton#segment:hover:!checked {{
    background-color: {p.btn_secondary_hover};
    color: {p.text_primary};
}}
QPushButton#primaryOutline {{
    background-color: transparent;
    color: {ACCENT};
    border: 1px solid {ACCENT};
    font-weight: bold;
}}
QPushButton#primaryOutline:hover {{
    background-color: {p.sidebar_active_bg};
}}
QPushButton#primaryOutline:disabled {{
    border-color: {p.btn_disabled};
    color: {p.text_muted};
}}
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {{
    background-color: {p.input_bg};
    border: 1px solid {p.input_border};
    border-radius: {RADIUS_INPUT}px;
    padding: 6px 8px;
    color: {p.text_primary};
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {p.focus_border};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.card_bg};
    color: {p.text_primary};
    border: 1px solid {p.card_border};
    selection-background-color: {ACCENT};
}}
QPushButton {{
    background-color: {p.btn_secondary};
    color: {p.text_primary};
    border: none;
    border-radius: {RADIUS_BUTTON}px;
    padding: 8px 14px;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {p.btn_secondary_hover};
}}
QPushButton:disabled {{
    background-color: {p.btn_disabled};
    color: {p.text_muted};
}}
QPushButton#primary {{
    background-color: {ACCENT};
    color: #FFFFFF;
    font-weight: bold;
    min-height: 40px;
    padding: 10px 18px;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#primary:disabled {{
    background-color: {p.btn_disabled};
    color: {p.text_muted};
}}
QPushButton#ghost {{
    background-color: transparent;
    color: {p.text_secondary};
}}
QPushButton#ghost:hover {{
    background-color: {p.btn_secondary};
    color: {p.text_primary};
}}
QPushButton#danger {{
    background-color: transparent;
    color: {DANGER};
}}
QPushButton#danger:hover {{
    background-color: {p.btn_secondary};
}}
QFrame#navPill {{
    background-color: {p.accent_subtle};
    border: none;
    border-left: 2px solid {ACCENT};
    border-radius: {RADIUS_BUTTON}px;
}}
QWidget#navBadgeSlot {{
    background: transparent;
}}
QLabel#navBadge {{
    font-size: {FONT_CAPTION}px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 10px;
    min-width: 18px;
}}
QLabel#navBadge[active="true"] {{
    color: {ACCENT};
    background-color: {p.accent_subtle};
}}
QLabel#navBadge[active="false"] {{
    color: {p.text_muted};
    background-color: {p.btn_secondary};
}}
QLabel#navBadge[empty="true"] {{
    color: transparent;
    background-color: transparent;
}}
QPushButton#nav {{
    background-color: transparent;
    color: {p.text_secondary};
    text-align: left;
    padding: 0 8px 0 12px;
    border: none;
    border-radius: 0;
}}
QPushButton#nav[navActive="true"] {{
    color: {ACCENT};
    background-color: transparent;
}}
QPushButton#nav:focus {{
    outline: none;
}}
QPushButton#sectionToggle {{
    background-color: transparent;
    color: {p.text_secondary};
    padding: 4px 8px;
    min-width: 28px;
    max-width: 32px;
    min-height: 24px;
}}
QPushButton#sectionToggle:hover {{
    background-color: {p.btn_secondary};
    color: {p.text_primary};
}}
QPushButton#nav:hover:!pressed {{
    color: {p.text_primary};
}}
QPushButton#link {{
    background-color: transparent;
    color: {p.link_color};
    text-align: left;
    padding: 0px 4px;
    min-height: 20px;
}}
QPushButton#link:hover {{
    text-decoration: underline;
}}
QPushButton#iconOnly {{
    padding: 6px;
    min-width: 32px;
    max-width: 40px;
}}
QProgressBar {{
    border: none;
    border-radius: 3px;
    background-color: {p.progress_track};
    height: 6px;
    text-align: center;
    color: {p.text_muted};
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: {p.scrollbar_bg};
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p.scrollbar_handle};
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {p.scrollbar_bg};
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {p.scrollbar_handle};
    min-width: 24px;
    border-radius: 5px;
}}
QCheckBox {{
    color: {p.text_primary};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {p.input_border};
    background: {p.input_bg};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox#switch {{
    spacing: 10px;
}}
QCheckBox#switch::indicator {{
    width: 40px;
    height: 22px;
    border-radius: 11px;
    border: 1px solid {p.input_border};
    background: {p.btn_secondary};
}}
QCheckBox#switch::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QFrame#compactRow {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {p.divider};
}}
QFrame#compactRow:hover {{
    background-color: {p.btn_secondary};
}}
QLabel[class="muted"] {{
    color: {p.text_muted};
    font-size: {FONT_CAPTION}px;
}}
QLabel[class="secondary"] {{
    color: {p.text_secondary};
}}
QLabel[class="fieldLabel"] {{
    color: {p.text_secondary};
    font-size: {FONT_CAPTION}px;
}}
QLabel#pageTitle {{
    font-size: {FONT_PAGE_TITLE}px;
    font-weight: 600;
    color: {p.text_primary};
}}
QLabel#sectionTitle {{
    font-size: {FONT_SECTION}px;
    font-weight: 600;
    color: {p.text_primary};
}}
QLabel#cardSectionTitle {{
    font-size: {FONT_SECTION}px;
    font-weight: 600;
    color: {p.text_primary};
}}
QLabel#durationBadge {{
    background-color: {p.overlay_badge_bg};
    color: {p.overlay_badge_text};
    padding: 2px 6px;
    border-radius: 4px;
    font-size: {FONT_CAPTION}px;
}}
QLabel#previewTitle {{
    font-weight: 600;
    font-size: 14px;
    color: {p.text_primary};
    background-color: transparent;
}}
QFrame#sidebar {{
    background-color: {p.sidebar_bg};
    max-width: {SIDEBAR_WIDTH}px;
    min-width: {SIDEBAR_WIDTH}px;
}}
QFrame#separator {{
    color: {p.card_border};
    max-height: 1px;
}}
QDialog {{
    background-color: {p.app_bg};
}}
"""


def build_dark_qss() -> str:
    p = DARK
    return f"""
QWidget {{
    background-color: {p.app_bg};
    color: {p.text_primary};
    font-family: {FONT_FAMILY};
    font-size: {FONT_BODY}px;
}}
QMainWindow {{
    background-color: {p.app_bg};
}}
{_shared_qss(p)}
"""


def build_light_qss() -> str:
    p = LIGHT
    return f"""
QWidget {{
    background-color: {p.app_bg};
    color: {p.text_primary};
    font-family: {FONT_FAMILY};
    font-size: {FONT_BODY}px;
}}
QMainWindow {{
    background-color: {p.app_bg};
}}
{_shared_qss(p)}
"""


def current_appearance_palette() -> ThemePalette:
    """Return light or dark palette from the application stylesheet."""
    app = QApplication.instance()
    sheet = app.styleSheet() if app is not None else ""
    return LIGHT if LIGHT.app_bg in sheet else DARK


def polish_widget(widget: QWidget) -> None:
    """Re-apply QSS after dynamic properties (class, objectName)."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def apply_theme(app: QApplication, appearance_mode: str) -> None:
    """Apply Fusion style + dark or light QSS."""
    app.setStyle("Fusion")
    base_font = QFont("Segoe UI", FONT_BODY)
    app.setFont(base_font)
    if appearance_mode == "light":
        app.setStyleSheet(build_light_qss())
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(LIGHT.app_bg))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(LIGHT.text_primary))
        palette.setColor(QPalette.ColorRole.Base, QColor(LIGHT.input_bg))
        palette.setColor(QPalette.ColorRole.Text, QColor(LIGHT.text_primary))
        app.setPalette(palette)
    else:
        app.setStyleSheet(build_dark_qss())
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(DARK.app_bg))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(DARK.text_primary))
        palette.setColor(QPalette.ColorRole.Base, QColor(DARK.input_bg))
        palette.setColor(QPalette.ColorRole.Text, QColor(DARK.text_primary))
        app.setPalette(palette)
