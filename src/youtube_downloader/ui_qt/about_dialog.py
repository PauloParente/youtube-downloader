"""About dialog."""

from __future__ import annotations

import sys
import webbrowser
from collections.abc import Callable

import yt_dlp
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.config import (
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    COPYRIGHT_LINE,
    GITHUB_REPO_URL,
    PROJECT_ROOT,
)
from youtube_downloader.core.ffmpeg_utils import find_ffmpeg_dir, is_bundled_ffmpeg
from youtube_downloader.core.text_utils import truncate_text
from youtube_downloader.ui_qt.widgets import GhostButton, PrimaryButton


def _build_about_text() -> str:
    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    try:
        from PySide6 import __version__ as qt_version
    except ImportError:
        qt_version = "?"
    if is_bundled_ffmpeg():
        ffmpeg_line = "FFmpeg: embutido (build .exe) ou pasta do app"
    else:
        ffmpeg_dir = find_ffmpeg_dir() or "não encontrado"
        ffmpeg_line = f"FFmpeg: {truncate_text(str(ffmpeg_dir), 56)}"
    run_mode = (
        "Aplicativo empacotado (.exe)"
        if getattr(sys, "frozen", False)
        else "Python (desenvolvimento)"
    )
    data_dir = truncate_text(str(PROJECT_ROOT.resolve()), 56)
    return "\n".join(
        [
            f"{APP_TITLE}  v{APP_VERSION}",
            APP_DESCRIPTION,
            COPYRIGHT_LINE,
            "",
            "Ambiente",
            f"  Python {python_version}",
            f"  PySide6 {qt_version}",
            f"  yt-dlp {yt_dlp.version.__version__}",
            f"  {ffmpeg_line}",
            f"  Modo: {run_mode}",
            "",
            "Dados locais",
            f"  Pasta do app: {data_dir}",
            "  settings.json, history.json, downloads/ e logs/ nesta pasta.",
            "",
            "Atalhos de teclado",
            "  Ctrl+V — colar URL na tela Downloads",
            "  Ctrl+, — abrir Configurações",
            "  Ctrl+1 — Downloads",
            "  Ctrl+2 — Fila",
            "  Ctrl+3 — Biblioteca",
            "  Ctrl+4 — Histórico",
            "  Ctrl+5 — Configurações",
        ]
    )


def show_about_dialog(
    parent: QWidget,
    *,
    on_open_logs: Callable[[], None],
) -> QDialog:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Sobre")
    dialog.setModal(True)
    dialog.resize(480, 500)

    layout = QVBoxLayout(dialog)
    header = QHBoxLayout()
    header.addWidget(QLabel("<b>Sobre</b>"))
    header.addStretch()
    close_hdr = GhostButton("✕")
    close_hdr.clicked.connect(dialog.close)
    header.addWidget(close_hdr)
    layout.addLayout(header)

    text = QTextEdit()
    text.setReadOnly(True)
    text.setPlainText(_build_about_text())
    layout.addWidget(text)

    buttons = QHBoxLayout()
    logs_btn = QPushButton("Ver logs")
    logs_btn.clicked.connect(on_open_logs)
    buttons.addWidget(logs_btn)
    gh_btn = QPushButton("GitHub")
    gh_btn.clicked.connect(lambda: webbrowser.open(GITHUB_REPO_URL))
    buttons.addWidget(gh_btn)
    buttons.addStretch()
    ok_btn = PrimaryButton("OK")
    ok_btn.clicked.connect(dialog.accept)
    buttons.addWidget(ok_btn)
    layout.addLayout(buttons)

    dialog.exec()
    return dialog
