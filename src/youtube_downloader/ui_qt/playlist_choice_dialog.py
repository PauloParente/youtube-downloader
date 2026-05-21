"""Dialog when a watch URL includes a playlist."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.core.playlist_urls import PlaylistMode

PlaylistChoice = Optional[PlaylistMode]


def ask_video_in_playlist_choice(
    parent: QWidget,
    *,
    playlist_count: int | None = None,
) -> PlaylistChoice:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Playlist detectada")
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    layout.addWidget(
        QLabel("Esta URL abre um vídeo dentro de uma playlist.\nO que deseja baixar?")
    )
    count_hint = ""
    if playlist_count is not None and playlist_count > 0:
        count_hint = f" ({playlist_count} vídeos)"

    result: dict[str, PlaylistChoice] = {"value": None}

    def choose(mode: PlaylistMode) -> None:
        result["value"] = mode
        dialog.accept()

    single_btn = QPushButton("Só este vídeo")
    single_btn.setObjectName("primary")
    single_btn.clicked.connect(lambda: choose("single"))
    layout.addWidget(single_btn)

    full_btn = QPushButton(f"Playlist inteira{count_hint}")
    full_btn.clicked.connect(lambda: choose("full"))
    layout.addWidget(full_btn)

    cancel_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    cancel_box.rejected.connect(dialog.reject)
    layout.addWidget(cancel_box)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return result["value"]
