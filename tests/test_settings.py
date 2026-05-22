import json
import sys
from pathlib import Path

import pytest

from youtube_downloader.core.settings import AppSettings, _coerce_settings, load_settings, save_settings


def test_coerce_settings_defaults_on_invalid_quality() -> None:
    settings = _coerce_settings({"quality": "4K-ultra"})
    assert settings.quality == AppSettings.defaults().quality


def test_coerce_activity_log_expanded() -> None:
    assert _coerce_settings({"activity_log_expanded": False}).activity_log_expanded is False
    assert _coerce_settings({}).activity_log_expanded is True


def test_coerce_sidebar_collapsed() -> None:
    assert _coerce_settings({"sidebar_collapsed": True}).sidebar_collapsed is True
    assert _coerce_settings({}).sidebar_collapsed is False


def test_coerce_focus_queue_on_download() -> None:
    assert _coerce_settings({"focus_queue_on_download": False}).focus_queue_on_download is False
    assert _coerce_settings({}).focus_queue_on_download is True


def _foreign_unwritable_path() -> str:
    if sys.platform == "win32":
        return r"Z:\no-such-volume\YouTubeDownloader\downloads"
    return "/home/outro-usuario-inexistente/PythonProject/downloads"


def test_resolve_output_dir_rejects_foreign_absolute_path(
    tmp_path: Path, monkeypatch
) -> None:
    import youtube_downloader.core.settings as settings_mod

    monkeypatch.setattr(settings_mod, "PROJECT_ROOT", tmp_path)
    foreign = _foreign_unwritable_path()
    resolved = settings_mod._resolve_output_dir(foreign)
    expected = (tmp_path / "downloads").resolve()
    assert Path(resolved) == expected


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
def test_resolve_output_dir_rejects_windows_path_on_posix(
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
        export_profile="max_quality",
    )
    save_settings(original)
    loaded = load_settings()
    assert loaded == original
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "download_playlist" not in data
