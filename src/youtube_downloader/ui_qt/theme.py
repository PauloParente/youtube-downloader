"""Visual theme (colors + QSS) aligned with the former CustomTkinter palette."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

APP_BG = "#121212"
CARD_BG = "#1E1E1E"
CARD_BORDER = "#2D2D2D"
INPUT_BG = "#252525"
INPUT_BORDER = "#3A3A3A"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#A0A0A0"
TEXT_MUTED = "#6B6B6B"
ACCENT = "#007BFF"
ACCENT_HOVER = "#0069D9"
BTN_SECONDARY = "#2D2D2D"
BTN_SECONDARY_HOVER = "#3D3D3D"
BTN_DISABLED = "#3A3A3A"
SIDEBAR_WIDTH = 220
SIDEBAR_BG = "#161616"
SIDEBAR_ACTIVE_BG = "#252528"

_DARK_QSS = f"""
QWidget {{
    background-color: {APP_BG};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI";
    font-size: 12px;
}}
QMainWindow {{
    background-color: {APP_BG};
}}
QFrame#card {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 8px;
}}
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {{
    background-color: {INPUT_BG};
    border: 1px solid {INPUT_BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    color: {TEXT_PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {APP_BG};
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
}}
QPushButton {{
    background-color: {BTN_SECONDARY};
    color: {TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {BTN_SECONDARY_HOVER};
}}
QPushButton:disabled {{
    background-color: {BTN_DISABLED};
    color: {TEXT_MUTED};
}}
QPushButton#primary {{
    background-color: {ACCENT};
    font-weight: bold;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#ghost {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
}}
QPushButton#nav {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    text-align: left;
    padding: 10px 12px;
}}
QPushButton#nav:checked {{
    background-color: {SIDEBAR_ACTIVE_BG};
    color: {ACCENT};
}}
QProgressBar {{
    border: none;
    border-radius: 3px;
    background-color: #2a2a2a;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {INPUT_BORDER};
    background: {INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QLabel#muted {{
    color: {TEXT_MUTED};
}}
QLabel#secondary {{
    color: {TEXT_SECONDARY};
}}
QFrame#sidebar {{
    background-color: {SIDEBAR_BG};
    max-width: {SIDEBAR_WIDTH}px;
    min-width: {SIDEBAR_WIDTH}px;
}}
"""

_LIGHT_QSS = f"""
QWidget {{
    background-color: #f5f5f5;
    color: #1a1a1a;
    font-family: "Segoe UI";
    font-size: 12px;
}}
QMainWindow {{
    background-color: #f5f5f5;
}}
QFrame#card {{
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
}}
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {{
    background-color: #ffffff;
    border: 1px solid #c8c8c8;
    border-radius: 6px;
    padding: 6px 8px;
    color: #1a1a1a;
}}
QPushButton {{
    background-color: #e8e8e8;
    color: #1a1a1a;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
}}
QPushButton#primary {{
    background-color: {ACCENT};
    color: #ffffff;
}}
QFrame#sidebar {{
    background-color: #ebebeb;
    max-width: {SIDEBAR_WIDTH}px;
    min-width: {SIDEBAR_WIDTH}px;
}}
"""


def apply_theme(app: QApplication, appearance_mode: str) -> None:
    """Apply dark or light QSS."""
    if appearance_mode == "light":
        app.setStyleSheet(_LIGHT_QSS)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f5f5f5"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1a1a1a"))
        app.setPalette(palette)
    else:
        app.setStyleSheet(_DARK_QSS)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(APP_BG))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
        app.setPalette(palette)
