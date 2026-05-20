import json
from pathlib import Path

from youtube_downloader.core.settings import AppSettings, _coerce_settings, load_settings, save_settings


def test_coerce_settings_defaults_on_invalid_quality() -> None:
    settings = _coerce_settings({"quality": "4K-ultra"})
    assert settings.quality == AppSettings.defaults().quality


def test_resolve_output_dir_rejects_foreign_absolute_path(
    tmp_path: Path, monkeypatch
) -> None:
    import youtube_downloader.core.settings as settings_mod

    monkeypatch.setattr(settings_mod, "PROJECT_ROOT", tmp_path)
    foreign = r"C:\Users\outro.usuario\PythonProject\dist\YouTubeDownloader\downloads"
    resolved = settings_mod._resolve_output_dir(foreign)
    expected = (tmp_path / "downloads").resolve()
    assert Path(resolved) == expected


def test_save_and_load_roundtrip(tmp_path: Path, monkeypatch) -> None:
    import youtube_downloader.core.settings as settings_mod

    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "SETTINGS_FILE", path)

    original = AppSettings(
        output_dir=str(tmp_path / "dl"),
        quality="720p",
        audio_only=True,
        download_playlist=True,
        export_profile="max_quality",
    )
    save_settings(original)
    loaded = load_settings()
    assert loaded == original
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["download_playlist"] is True
