"""extract_url_from_drop_text helper."""

from youtube_downloader.core.text_utils import extract_url_from_drop_text


def test_extract_from_plain_text() -> None:
    text = "Check this https://www.youtube.com/watch?v=dQw4w9WgXcQ please"
    assert extract_url_from_drop_text(text) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_extract_from_uri_list() -> None:
    text = "file:///C:/tmp/foo.txt\r\nhttps://youtu.be/abc123_xyz\r\n"
    assert extract_url_from_drop_text(text) == "https://youtu.be/abc123_xyz"


def test_extract_empty() -> None:
    assert extract_url_from_drop_text("") == ""
