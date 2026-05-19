"""Preferences dialog for default download settings."""

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
    CARD_BORDER,
    ENTRY_STYLE,
    FONT_BODY,
    FONT_SMALL,
    INPUT_BORDER,
    OUTLINE_BTN,
    PRIMARY_BTN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class PreferencesDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        settings: AppSettings,
        on_save: Callable[[AppSettings], None],
    ) -> None:
        super().__init__(parent)
        self._on_save = on_save
        self._output_dir = tk.StringVar(value=settings.output_dir)
        self._audio_only_var = tk.BooleanVar(value=settings.audio_only)
        self._playlist_var = tk.BooleanVar(value=settings.download_playlist)

        self.title("Preferências")
        self.geometry("520x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=APP_BG)

        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Preferências",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Padrões usados ao abrir o aplicativo.",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        ctk.CTkFrame(self, height=1, fg_color=CARD_BORDER).grid(
            row=1, column=0, sticky="ew", padx=24, pady=(16, 0)
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="ew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Pasta padrão de downloads",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        path_row = ctk.CTkFrame(body, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        path_row.grid_columnconfigure(0, weight=1)
        self._folder_entry = ctk.CTkEntry(
            path_row,
            textvariable=self._output_dir,
            state="readonly",
            **ENTRY_STYLE,
        )
        self._folder_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(
            path_row,
            text="Escolher",
            width=90,
            command=self._browse_folder,
            **OUTLINE_BTN,
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            body,
            text="Qualidade padrão",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))
        self._quality_combo = ctk.CTkComboBox(
            body,
            values=QUALITY_COMBO_VALUES,
            state="readonly",
            width=280,
            dropdown_fg_color=APP_BG,
            button_color=BTN_SECONDARY,
            button_hover_color=BTN_SECONDARY_HOVER,
            border_color=INPUT_BORDER,
            fg_color=ENTRY_STYLE["fg_color"],
            text_color=TEXT_PRIMARY,
        )
        display = QUALITY_DISPLAY_LABELS.get(
            settings.quality, QUALITY_DISPLAY_LABELS[QUALITY_OPTIONS[0]]
        )
        self._quality_combo.set(display)
        self._quality_combo.grid(row=3, column=0, sticky="w", pady=(0, 14))

        self._audio_checkbox = ctk.CTkCheckBox(
            body,
            text="Somente áudio por padrão",
            variable=self._audio_only_var,
            command=self._on_audio_toggle,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=INPUT_BORDER,
        )
        self._audio_checkbox.grid(row=4, column=0, sticky="w", pady=4)

        self._playlist_checkbox = ctk.CTkCheckBox(
            body,
            text="Baixar playlist inteira por padrão",
            variable=self._playlist_var,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=INPUT_BORDER,
        )
        self._playlist_checkbox.grid(row=5, column=0, sticky="w", pady=4)
        self._on_audio_toggle()

        ctk.CTkFrame(self, height=1, fg_color=CARD_BORDER).grid(
            row=3, column=0, sticky="ew", padx=24
        )

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=24, pady=(16, 20))
        btn_row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            btn_row,
            text="Restaurar padrões",
            command=self._restore_defaults,
            width=140,
            **OUTLINE_BTN,
        ).grid(row=0, column=0, sticky="w")
        right = ctk.CTkFrame(btn_row, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            right,
            text="Cancelar",
            width=100,
            command=self.destroy,
            **OUTLINE_BTN,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            right,
            text="Salvar",
            width=100,
            command=self._save,
            **PRIMARY_BTN,
        ).grid(row=0, column=1)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _on_audio_toggle(self) -> None:
        if self._audio_only_var.get():
            self._quality_combo.configure(state="disabled")
        else:
            self._quality_combo.configure(state="readonly")

    def _browse_folder(self) -> None:
        initial = self._output_dir.get().strip() or str(DEFAULT_DOWNLOADS_DIR)
        folder = filedialog.askdirectory(
            title="Pasta padrão de downloads",
            initialdir=initial,
        )
        if folder:
            self._output_dir.set(folder)

    def _restore_defaults(self) -> None:
        defaults = AppSettings.defaults()
        self._output_dir.set(defaults.output_dir)
        self._audio_only_var.set(defaults.audio_only)
        self._playlist_var.set(defaults.download_playlist)
        self._quality_combo.set(QUALITY_DISPLAY_LABELS[defaults.quality])
        self._on_audio_toggle()

    def _collect(self) -> AppSettings:
        display = self._quality_combo.get()
        quality = QUALITY_FROM_DISPLAY.get(display, QUALITY_OPTIONS[0])
        return AppSettings(
            output_dir=self._output_dir.get().strip() or str(DEFAULT_DOWNLOADS_DIR),
            quality=quality,
            audio_only=self._audio_only_var.get(),
            download_playlist=self._playlist_var.get(),
        )

    def _save(self) -> None:
        self._on_save(self._collect())
        self.destroy()
