import os
import tempfile

from youtube_downloader.config import QUALITY_DISPLAY_LABELS, QUALITY_FORMATS, QUALITY_OPTIONS
from youtube_downloader.core.downloader import (
    YoutubeDownloader,
    cleanup_partial_download_files,
)


def test_is_intermediate_fragment() -> None:
    assert YoutubeDownloader._is_intermediate_fragment("Title.f248.webm")
    assert not YoutubeDownloader._is_intermediate_fragment("Title.mp4")


def test_quality_display_labels_cover_all_options() -> None:
    assert set(QUALITY_DISPLAY_LABELS.keys()) == set(QUALITY_OPTIONS)
    assert len(QUALITY_DISPLAY_LABELS) == len(set(QUALITY_DISPLAY_LABELS.values()))


def test_quality_formats_prefer_dash_over_progressive_mp4() -> None:
    for name, fmt in QUALITY_FORMATS.items():
        first = fmt.split("/")[0]
        assert first.startswith("bestvideo"), (
            f"{name!r} deve começar com bestvideo, obteve: {first!r}"
        )
        assert "best[" not in first, (
            f"{name!r} não deve priorizar best[...] combinado: {first!r}"
        )


def test_find_merge_orphans() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "video.f140.m4a"), "w", encoding="utf-8").close()
        open(os.path.join(tmp, "final.mp4"), "w", encoding="utf-8").close()
        orphans = YoutubeDownloader._find_merge_orphans(tmp)
        assert len(orphans) == 1
        assert "f140" in orphans[0]


def test_cleanup_partial_download_files_tracked_and_temp() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tracked = os.path.join(tmp, "clip.webm")
        part = os.path.join(tmp, "clip.mp4.part")
        orphan = os.path.join(tmp, "clip.f251.webm")
        keep = os.path.join(tmp, "other-done.mp4")
        for path in (tracked, part, orphan, keep):
            open(path, "w", encoding="utf-8").close()

        removed = cleanup_partial_download_files(tmp, [tracked])

        assert not os.path.exists(tracked)
        assert not os.path.exists(part)
        assert not os.path.exists(orphan)
        assert os.path.exists(keep)
        assert tracked in removed
