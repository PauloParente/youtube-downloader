"""Full-page settings view (Configurações)."""

from collections.abc import Callable
from tkinter import filedialog

import customtkinter as ctk
import tkinter as tk

from youtube_downloader.config import (
    DEFAULT_DOWNLOADS_DIR,
    QUALITY_COMBO_VALUES,
    QUALITY_DISPLAY_LABELS,
    QUALITY_FROM_DISPLAY,
    QUALITY_OPTIONS,
)
from youtube_downloader.core.settings import AppSettings
from youtube_downloader.ui.theme import (
    ACCENT,
    ACCENT_HOVER,
    APP_BG,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    CARD_STYLE,
    ENTRY_STYLE,
    INPUT_BORDER,
    OUTLINE_BTN,
    PRIMARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
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


class SettingsView(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_save: Callable[[AppSettings], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_save = on_save
        self.grid_columnconfigure(0, weight=1)

        self._output_dir = tk.StringVar()
        self._bandwidth_var = tk.StringVar(value="0")
        self._notify_var = tk.BooleanVar(value=True)
        self._subtitles_var = tk.BooleanVar(value=False)
        self._playlist_var = tk.BooleanVar(value=False)
        self._audio_only_var = tk.BooleanVar(value=False)

        pad = 24
        ctk.CTkLabel(
            self,
            text="Configurações",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=pad, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Ajuste o comportamento do aplicativo para otimizar seu fluxo de trabalho.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w",
            wraplength=640,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=pad, pady=(0, 20))

        general_body = self._add_card(
            2, "⚙", "Geral", pad, pady_bottom=16
        )
        self._field_label(general_body, 0, "Pasta padrão de download")
        path_row = ctk.CTkFrame(general_body, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        path_row.grid_columnconfigure(0, weight=1)
        self._folder_entry = ctk.CTkEntry(
            path_row, textvariable=self._output_dir, state="readonly", **ENTRY_STYLE
        )
        self._folder_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(
            path_row,
            text="📁  Procurar",
            width=110,
            command=self._browse_folder,
            **OUTLINE_BTN,
        ).grid(row=0, column=1)

        self._field_label(general_body, 2, "Tema da interface")
        self._dark_theme_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(
            general_body,
            text="Modo escuro",
            variable=self._dark_theme_var,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_PRIMARY,
        ).grid(row=3, column=0, sticky="w", pady=(0, 12))

        self._field_label(general_body, 4, "Idioma das legendas")
        self._language_combo = self._combo(general_body, _LANGUAGE_OPTIONS)
        self._language_combo.grid(row=5, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(
            general_body,
            text="Usado ao baixar legendas; não altera os textos da interface.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        ).grid(row=6, column=0, sticky="w", pady=(0, 4))

        quality_body = self._add_card(
            3, "HQ", "Qualidade e Formato", pad, pady_bottom=16
        )
        quality_body.grid_columnconfigure((0, 1), weight=1)

        self._field_label(quality_body, 0, "Qualidade de Vídeo Padrão", columnspan=1)
        self._quality_combo = self._combo(quality_body, QUALITY_COMBO_VALUES)
        self._quality_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 4))
        ctk.CTkLabel(
            quality_body,
            text="Define a resolução preferida se disponível.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 12))

        self._field_label(quality_body, 0, "Formato de Vídeo Padrão", column=1)
        self._video_format_combo = self._combo(quality_body, _VIDEO_FORMAT_OPTIONS)
        self._video_format_combo.grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 4)
        )

        self._field_label(quality_body, 3, "Perfil de exportação", columnspan=2)
        self._export_profile_combo = self._combo(quality_body, _EXPORT_PROFILE_OPTIONS)
        self._export_profile_combo.grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )
        ctk.CTkLabel(
            quality_body,
            text=(
                "Compatível: abre no Filmes e TV do Windows (H.264 + AAC). "
                "Melhor qualidade: pode exigir VLC."
            ),
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._webm_compat_hint = ctk.CTkLabel(
            quality_body,
            text="Para o reprodutor do Windows, prefira MP4 com perfil Compatível.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        )
        self._webm_compat_hint.grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self._video_format_combo.configure(command=self._on_video_format_changed)
        self._on_video_format_changed(self._video_format_combo.get())

        self._field_label(quality_body, 7, "Qualidade de Áudio Padrão")
        self._audio_bitrate_combo = self._combo(quality_body, _AUDIO_BITRATE_OPTIONS)
        self._audio_bitrate_combo.grid(
            row=8, column=0, sticky="ew", padx=(0, 8), pady=(0, 12)
        )

        self._field_label(quality_body, 7, "Formato de Áudio (Apenas Áudio)", column=1)
        self._audio_format_combo = self._combo(quality_body, ["MP3"])
        self._audio_format_combo.grid(row=8, column=1, sticky="ew", padx=(8, 0), pady=(0, 4))
        self._audio_format_combo.configure(state="disabled")

        self._audio_only_switch = ctk.CTkSwitch(
            quality_body,
            text="Modo somente áudio (MP3) por padrão",
            variable=self._audio_only_var,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_PRIMARY,
        )
        self._audio_only_switch.grid(row=9, column=0, columnspan=2, sticky="w", pady=(4, 0))

        advanced_body = self._add_card(4, "◈", "Avançado", pad, pady_bottom=12)
        self._field_label(advanced_body, 0, "Limite de Largura de Banda (KB/s)")
        bw_row = ctk.CTkFrame(advanced_body, fg_color="transparent")
        bw_row.grid(row=1, column=0, sticky="w", pady=(0, 14))
        self._bandwidth_entry = ctk.CTkEntry(
            bw_row, textvariable=self._bandwidth_var, width=120, **ENTRY_STYLE
        )
        self._bandwidth_entry.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            bw_row,
            text="0 significa sem limite.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        self._add_toggle_row(
            advanced_body,
            2,
            "Notificações no Sistema",
            "Mostrar balão de notificação quando o download concluir.",
            self._notify_var,
        )
        self._add_toggle_row(
            advanced_body,
            4,
            "Download Automático de Legendas",
            "Tentar baixar legendas PT-BR sempre que disponíveis.",
            self._subtitles_var,
        )
        self._add_toggle_row(
            advanced_body,
            6,
            "Baixar playlist inteira por padrão",
            "Ao colar link de playlist, marcar opção automaticamente.",
            self._playlist_var,
        )

        self._field_label(advanced_body, 8, "Arquivo de cookies (cookies.txt)")
        cookies_row = ctk.CTkFrame(advanced_body, fg_color="transparent")
        cookies_row.grid(row=9, column=0, sticky="ew", pady=(0, 8))
        cookies_row.grid_columnconfigure(0, weight=1)
        self._cookies_var = tk.StringVar()
        ctk.CTkEntry(
            cookies_row,
            textvariable=self._cookies_var,
            placeholder_text="Caminho para cookies.txt (opcional)",
            **ENTRY_STYLE,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            cookies_row,
            text="📁",
            width=40,
            command=self._browse_cookies,
            **OUTLINE_BTN,
        ).grid(row=0, column=1)
        ctk.CTkLabel(
            advanced_body,
            text="Exporte cookies do navegador para conteúdo restrito. Use por sua conta e risco.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        ).grid(row=10, column=0, sticky="w", pady=(0, 4))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=5, column=0, sticky="ew", padx=pad, pady=(8, 24))
        ctk.CTkButton(
            btn_row,
            text="Restaurar padrões",
            command=self._restore_defaults,
            width=150,
            **OUTLINE_BTN,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="Salvar alterações", command=self._save, width=160, **PRIMARY_BTN
        ).pack(side="right")

    def _add_card(
        self,
        row: int,
        icon: str,
        title: str,
        pad: int,
        *,
        pady_bottom: int,
    ) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self, **CARD_STYLE)
        card.grid(row=row, column=0, sticky="ew", padx=pad, pady=(0, pady_bottom))
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 10))
        ctk.CTkLabel(
            header,
            text=icon,
            width=28,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT,
            anchor="w",
        ).pack(side="left")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        body.grid_columnconfigure(0, weight=1)
        return body

    @staticmethod
    def _field_label(
        parent: ctk.CTkFrame,
        row: int,
        text: str,
        *,
        column: int = 0,
        columnspan: int = 1,
    ) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="w",
            pady=(0, 6),
            padx=(0, 0) if column == 0 else (8, 0),
        )

    def _combo(self, parent: ctk.CTkFrame, values: list[str]) -> ctk.CTkComboBox:
        return ctk.CTkComboBox(
            parent,
            values=values,
            state="readonly",
            dropdown_fg_color=APP_BG,
            button_color=BTN_SECONDARY,
            button_hover_color=BTN_SECONDARY_HOVER,
            border_color=INPUT_BORDER,
            fg_color=ENTRY_STYLE["fg_color"],
            text_color=TEXT_PRIMARY,
        )

    def _add_toggle_row(
        self,
        parent: ctk.CTkFrame,
        row: int,
        title: str,
        subtitle: str,
        variable: tk.BooleanVar,
    ) -> None:
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, sticky="ew", pady=8)
        row_frame.grid_columnconfigure(0, weight=1)

        text_col = ctk.CTkFrame(row_frame, fg_color="transparent")
        text_col.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            text_col,
            text=title,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            text_col,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=480,
            justify="left",
        ).pack(anchor="w")

        ctk.CTkSwitch(
            row_frame,
            text="",
            variable=variable,
            width=44,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        ).grid(row=0, column=1, sticky="e")

    def _on_video_format_changed(self, choice: str) -> None:
        is_webm = choice == "WebM"
        if is_webm:
            self._webm_compat_hint.grid()
        else:
            self._webm_compat_hint.grid_remove()

    def load_settings(self, settings: AppSettings) -> None:
        self._output_dir.set(settings.output_dir)
        self._dark_theme_var.set(settings.appearance_mode == "dark")
        self._language_combo.set(
            _LANGUAGE_TO_LABEL.get(settings.language, _LANGUAGE_OPTIONS[0])
        )
        self._cookies_var.set(settings.cookies_file)
        self._quality_combo.set(
            QUALITY_DISPLAY_LABELS.get(settings.quality, QUALITY_DISPLAY_LABELS["1080p"])
        )
        vf = "MP4 (Recomendado)" if settings.video_format == "mp4" else "WebM"
        self._video_format_combo.set(vf)
        self._on_video_format_changed(vf)
        self._export_profile_combo.set(
            _EXPORT_PROFILE_TO_LABEL.get(
                settings.export_profile, _EXPORT_PROFILE_OPTIONS[0]
            )
        )
        self._audio_bitrate_combo.set(
            _AUDIO_BITRATE_TO_LABEL.get(settings.audio_bitrate, _AUDIO_BITRATE_OPTIONS[1])
        )
        self._bandwidth_var.set(str(settings.bandwidth_limit_kbps))
        self._notify_var.set(settings.notify_on_complete)
        self._subtitles_var.set(settings.auto_download_subtitles)
        self._playlist_var.set(settings.download_playlist)
        self._audio_only_var.set(settings.audio_only)

    def _browse_folder(self) -> None:
        initial = self._output_dir.get().strip() or str(DEFAULT_DOWNLOADS_DIR)
        folder = filedialog.askdirectory(
            title="Pasta padrão de download",
            initialdir=initial,
        )
        if folder:
            self._output_dir.set(folder)

    def _browse_cookies(self) -> None:
        path = filedialog.askopenfilename(
            title="Arquivo cookies.txt",
            filetypes=[("Netscape cookies", "*.txt"), ("Todos", "*.*")],
        )
        if path:
            self._cookies_var.set(path)

    def _restore_defaults(self) -> None:
        self.load_settings(AppSettings.defaults())

    def collect_settings(self) -> AppSettings:
        try:
            bandwidth = int(self._bandwidth_var.get().strip() or "0")
        except ValueError:
            bandwidth = 0
        if bandwidth < 0:
            bandwidth = 0

        quality_display = self._quality_combo.get()
        quality = QUALITY_FROM_DISPLAY.get(quality_display, QUALITY_OPTIONS[0])
        lang = _LANGUAGE_FROM_LABEL.get(
            self._language_combo.get(), "pt-BR"
        )
        vf = _VIDEO_FORMAT_FROM_LABEL.get(
            self._video_format_combo.get(), "mp4"
        )
        ab = _AUDIO_BITRATE_FROM_LABEL.get(
            self._audio_bitrate_combo.get(), "192"
        )
        export_profile = _EXPORT_PROFILE_FROM_LABEL.get(
            self._export_profile_combo.get(), "compatible"
        )

        return AppSettings(
            output_dir=self._output_dir.get().strip() or str(DEFAULT_DOWNLOADS_DIR),
            quality=quality,
            audio_only=self._audio_only_var.get(),
            download_playlist=self._playlist_var.get(),
            language=lang,
            video_format=vf,
            export_profile=export_profile,
            audio_bitrate=ab,
            bandwidth_limit_kbps=bandwidth,
            notify_on_complete=self._notify_var.get(),
            auto_download_subtitles=self._subtitles_var.get(),
            appearance_mode="dark" if self._dark_theme_var.get() else "light",
            cookies_file=self._cookies_var.get().strip(),
        )

    def _save(self) -> None:
        self._on_save(self.collect_settings())
