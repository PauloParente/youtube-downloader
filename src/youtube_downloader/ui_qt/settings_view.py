"""Settings page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from youtube_downloader.config import (
    DEFAULT_DOWNLOADS_DIR,
    QUALITY_COMBO_VALUES,
    QUALITY_DISPLAY_LABELS,
    QUALITY_FROM_DISPLAY,
    QUALITY_OPTIONS,
)
from youtube_downloader.core.settings import AppSettings
from youtube_downloader.ui_qt.icons import icon_on_button, themed_icon
from youtube_downloader.ui_qt.theme_tokens import PAGE_MARGINS
from youtube_downloader.ui_qt.widgets import (
    Card,
    PageHeader,
    PrimaryButton,
    apply_page_margins,
    field_label,
    muted_label,
)

_LANGUAGE_OPTIONS = ["Português (Brasil)", "English"]
_LANGUAGE_FROM_LABEL = {"Português (Brasil)": "pt-BR", "English": "en"}
_LANGUAGE_TO_LABEL = {v: k for k, v in _LANGUAGE_FROM_LABEL.items()}
_VIDEO_FORMAT_OPTIONS = ["MP4 (Recomendado)", "WebM"]
_VIDEO_FORMAT_FROM_LABEL = {"MP4 (Recomendado)": "mp4", "WebM": "webm"}
_AUDIO_BITRATE_OPTIONS = ["128 kbps", "192 kbps (Padrão)", "320 kbps"]
_AUDIO_BITRATE_FROM_LABEL = {
    "128 kbps": "128",
    "192 kbps (Padrão)": "192",
    "320 kbps": "320",
}
_AUDIO_BITRATE_TO_LABEL = {v: k for k, v in _AUDIO_BITRATE_FROM_LABEL.items()}
_EXPORT_PROFILE_OPTIONS = [
    "Compatível com Windows (H.264)",
    "Melhor qualidade (AV1/VP9)",
]
_EXPORT_PROFILE_FROM_LABEL = {
    "Compatível com Windows (H.264)": "compatible",
    "Melhor qualidade (AV1/VP9)": "max_quality",
}
_EXPORT_PROFILE_TO_LABEL = {v: k for k, v in _EXPORT_PROFILE_FROM_LABEL.items()}


class SettingsView(QWidget):
    def __init__(
        self,
        on_save: Callable[[AppSettings], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_save = on_save
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        apply_page_margins(layout)

        layout.addWidget(
            PageHeader(
                "Configurações",
                "Ajuste o comportamento do aplicativo para otimizar seu fluxo de trabalho.",
            )
        )

        general = self._card("general", "Geral", layout)
        gl = general.layout()
        gl.addWidget(field_label("Pasta padrão de download"))
        path_row = QHBoxLayout()
        self._folder_entry = QLineEdit()
        self._folder_entry.setReadOnly(True)
        path_row.addWidget(self._folder_entry, stretch=1)
        browse = QPushButton("Procurar")
        icon_on_button(browse, "folder", size=18)
        browse.clicked.connect(self._browse_folder)
        path_row.addWidget(browse)
        gl.addLayout(path_row)
        gl.addWidget(field_label("Tema da interface"))
        self._dark_check = QCheckBox("Modo escuro")
        self._dark_check.setObjectName("switch")
        self._dark_check.setChecked(True)
        gl.addWidget(self._dark_check)
        gl.addWidget(field_label("Idioma das legendas"))
        self._language_combo = QComboBox()
        self._language_combo.addItems(_LANGUAGE_OPTIONS)
        gl.addWidget(self._language_combo)

        quality = self._card("quality", "Qualidade e Formato", layout)
        ql = quality.layout()
        ql.addWidget(field_label("Qualidade de Vídeo Padrão"))
        self._quality_combo = QComboBox()
        self._quality_combo.addItems(QUALITY_COMBO_VALUES)
        ql.addWidget(self._quality_combo)
        ql.addWidget(field_label("Formato de Vídeo Padrão"))
        self._video_format_combo = QComboBox()
        self._video_format_combo.addItems(_VIDEO_FORMAT_OPTIONS)
        self._video_format_combo.currentTextChanged.connect(self._on_video_format_changed)
        ql.addWidget(self._video_format_combo)
        self._webm_hint = muted_label(
            "Para o reprodutor do Windows, prefira MP4 com perfil Compatível."
        )
        self._webm_hint.hide()
        ql.addWidget(self._webm_hint)
        ql.addWidget(field_label("Perfil de exportação"))
        self._export_profile_combo = QComboBox()
        self._export_profile_combo.addItems(_EXPORT_PROFILE_OPTIONS)
        ql.addWidget(self._export_profile_combo)
        ql.addWidget(field_label("Qualidade de Áudio Padrão"))
        self._audio_bitrate_combo = QComboBox()
        self._audio_bitrate_combo.addItems(_AUDIO_BITRATE_OPTIONS)
        ql.addWidget(self._audio_bitrate_combo)
        self._audio_only_check = QCheckBox("Modo somente áudio (MP3) por padrão")
        self._audio_only_check.setObjectName("switch")
        ql.addWidget(self._audio_only_check)

        advanced = self._card("advanced", "Avançado", layout)
        al = advanced.layout()
        al.addWidget(field_label("Limite de Largura de Banda (KB/s)"))
        self._bandwidth_entry = QLineEdit("0")
        al.addWidget(self._bandwidth_entry)
        self._notify_check = QCheckBox("Notificações no Sistema")
        self._notify_check.setObjectName("switch")
        self._notify_check.setChecked(True)
        al.addWidget(self._notify_check)
        self._subtitles_check = QCheckBox("Download Automático de Legendas")
        self._subtitles_check.setObjectName("switch")
        al.addWidget(self._subtitles_check)
        al.addWidget(field_label("Arquivo de cookies (cookies.txt)"))
        cookies_row = QHBoxLayout()
        self._cookies_entry = QLineEdit()
        self._cookies_entry.setPlaceholderText("Caminho para cookies.txt (opcional)")
        cookies_row.addWidget(self._cookies_entry, stretch=1)
        cookies_btn = QPushButton()
        cookies_btn.setObjectName("iconOnly")
        icon_on_button(cookies_btn, "folder", size=18)
        cookies_btn.clicked.connect(self._browse_cookies)
        cookies_row.addWidget(cookies_btn)
        al.addLayout(cookies_row)

        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        dock = QFrame()
        dock.setObjectName("actionDock")
        dock_l, _, dock_r, dock_b = PAGE_MARGINS
        dock_layout = QVBoxLayout(dock)
        dock_layout.setContentsMargins(dock_l, 12, dock_r, dock_b)
        btn_row = QHBoxLayout()
        restore = QPushButton("Restaurar padrões")
        restore.clicked.connect(self._restore_defaults)
        btn_row.addWidget(restore)
        btn_row.addStretch()
        save_btn = PrimaryButton("Salvar alterações")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        dock_layout.addLayout(btn_row)
        outer.addWidget(dock)

    def _card(self, icon_name: str, title: str, parent_layout: QVBoxLayout) -> QWidget:
        card = Card()
        header_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(themed_icon(icon_name, 20).pixmap(20, 20))
        header_row.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardSectionTitle")
        header_row.addWidget(title_lbl)
        header_row.addStretch()
        card.body_layout.addLayout(header_row)
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)
        card.body_layout.addWidget(body)
        parent_layout.addWidget(card)
        return body

    def _on_video_format_changed(self, choice: str) -> None:
        if choice == "WebM":
            self._webm_hint.show()
        else:
            self._webm_hint.hide()

    def load_settings(self, settings: AppSettings) -> None:
        self._folder_entry.setText(settings.output_dir)
        self._dark_check.setChecked(settings.appearance_mode == "dark")
        self._language_combo.setCurrentText(
            _LANGUAGE_TO_LABEL.get(settings.language, _LANGUAGE_OPTIONS[0])
        )
        self._quality_combo.setCurrentText(
            QUALITY_DISPLAY_LABELS.get(settings.quality, QUALITY_DISPLAY_LABELS["1080p"])
        )
        vf = "MP4 (Recomendado)" if settings.video_format == "mp4" else "WebM"
        self._video_format_combo.setCurrentText(vf)
        self._on_video_format_changed(vf)
        self._export_profile_combo.setCurrentText(
            _EXPORT_PROFILE_TO_LABEL.get(settings.export_profile, _EXPORT_PROFILE_OPTIONS[0])
        )
        self._audio_bitrate_combo.setCurrentText(
            _AUDIO_BITRATE_TO_LABEL.get(settings.audio_bitrate, _AUDIO_BITRATE_OPTIONS[1])
        )
        self._bandwidth_entry.setText(str(settings.bandwidth_limit_kbps))
        self._notify_check.setChecked(settings.notify_on_complete)
        self._subtitles_check.setChecked(settings.auto_download_subtitles)
        self._audio_only_check.setChecked(settings.audio_only)
        self._cookies_entry.setText(settings.cookies_file)

    def _browse_folder(self) -> None:
        initial = self._folder_entry.text().strip() or str(DEFAULT_DOWNLOADS_DIR)
        folder = QFileDialog.getExistingDirectory(self, "Pasta padrão de download", initial)
        if folder:
            self._folder_entry.setText(folder)

    def _browse_cookies(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Arquivo cookies.txt", filter="Netscape cookies (*.txt);;Todos (*.*)"
        )
        if path:
            self._cookies_entry.setText(path)

    def _restore_defaults(self) -> None:
        self.load_settings(AppSettings.defaults())

    def collect_settings(self) -> AppSettings:
        try:
            bandwidth = int(self._bandwidth_entry.text().strip() or "0")
        except ValueError:
            bandwidth = 0
        if bandwidth < 0:
            bandwidth = 0
        quality_display = self._quality_combo.currentText()
        quality = QUALITY_FROM_DISPLAY.get(quality_display, QUALITY_OPTIONS[0])
        return AppSettings(
            output_dir=self._folder_entry.text().strip() or str(DEFAULT_DOWNLOADS_DIR),
            quality=quality,
            audio_only=self._audio_only_check.isChecked(),
            language=_LANGUAGE_FROM_LABEL.get(
                self._language_combo.currentText(), "pt-BR"
            ),
            video_format=_VIDEO_FORMAT_FROM_LABEL.get(
                self._video_format_combo.currentText(), "mp4"
            ),
            export_profile=_EXPORT_PROFILE_FROM_LABEL.get(
                self._export_profile_combo.currentText(), "compatible"
            ),
            audio_bitrate=_AUDIO_BITRATE_FROM_LABEL.get(
                self._audio_bitrate_combo.currentText(), "192"
            ),
            bandwidth_limit_kbps=bandwidth,
            notify_on_complete=self._notify_check.isChecked(),
            auto_download_subtitles=self._subtitles_check.isChecked(),
            appearance_mode="dark" if self._dark_check.isChecked() else "light",
            cookies_file=self._cookies_entry.text().strip(),
        )

    def _save(self) -> None:
        self._on_save(self.collect_settings())
