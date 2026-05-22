"""Theme QSS generation."""

from youtube_downloader.ui_qt.theme import build_dark_qss, build_light_qss
from youtube_downloader.ui_qt.theme_tokens import ACCENT, DARK, LIGHT


def test_dark_qss_contains_tokens() -> None:
    qss = build_dark_qss()
    assert DARK.app_bg in qss
    assert ACCENT in qss
    assert 'QLabel[class="muted"]' in qss
    assert "QPushButton#primary" in qss
    assert "QFrame#card" in qss


def test_light_qss_parity() -> None:
    qss = build_light_qss()
    assert LIGHT.app_bg in qss
    assert "QPushButton#appearanceToggle" in qss
    assert "QFrame#navPill" in qss
    assert "border-left: 2px solid" in qss
    assert "QLabel#navBadge" in qss
    assert 'QPushButton#nav[navActive="true"]' in qss
    assert "QPushButton#nav" in qss
    assert "QCheckBox::indicator:checked" in qss
    assert "QScrollBar:vertical" in qss


def test_dark_qss_new_selectors() -> None:
    qss = build_dark_qss()
    assert "QFrame#sidebarDivider" in qss
    assert "QFrame#titleBarDivider" in qss
    assert "QWidget#windowRoot" in qss
    assert "QLabel#titleBarTitle" in qss
    assert DARK.divider in qss
    assert 'QLabel[class="fieldLabel"]' in qss
    assert "QFrame#surfaceInset" in qss
    assert "QPlainTextEdit#logInset" in qss
    assert "QPushButton#sectionToggle" in qss
    assert "QLineEdit#urlHero" in qss
    assert "QFrame#progressStrip" in qss
    assert "QFrame#skeletonLine" in qss
    assert "QLabel#activityLastLine" in qss
    assert "QFrame#actionDock" in qss
    assert "QPushButton#segment" in qss
    assert "QPushButton#primaryOutline" in qss
    assert DARK.accent_subtle in qss
    assert "QCheckBox#switch" in qss
    assert "QFrame#statusBanner" in qss
    assert "QFrame#statusBanner QLabel" in qss
    assert "statusBannerClose" in qss
    assert "QLineEdit#filterInput" in qss
    assert "QFrame#compactRow" in qss
    assert "QFrame#downloadAlert" in qss
    assert "QFrame#previewEmpty" in qss
    assert "QFrame#previewEmptyIcon" in qss
    assert DARK.alert_info_bg in qss
    assert DARK.btn_secondary_border in qss
    assert "destinationChip" in qss
    assert "QFrame#customTitleBar" in qss
    assert "QFrame#customTitleBar QPushButton#titleBarButton" in qss
    assert "titleBarButtonClose:pressed" in qss
    assert "QFrame#card QWidget#downloadOptionsBar" in qss
    assert "QFrame#card QWidget#segmentedControl" in qss
    assert "QPushButton#appearanceToggle" in qss
