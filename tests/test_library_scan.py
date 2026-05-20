from youtube_downloader.core.library_scan import scan_library_folder


def test_scan_library_folder_lists_media(tmp_path) -> None:
    (tmp_path / "clip.mp4").write_bytes(b"x" * 100)
    (tmp_path / "note.txt").write_text("skip", encoding="utf-8")
    items = scan_library_folder(str(tmp_path))
    assert len(items) == 1
    assert items[0].name == "clip"
    assert items[0].format_ext == "MP4"
