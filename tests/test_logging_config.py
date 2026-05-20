"""Tests for logging hooks."""

import logging
import sys

from youtube_downloader.core.logging_config import install_ui_exception_logging


def test_install_ui_exception_logging_records_callback_errors(caplog) -> None:
    caplog.set_level(logging.CRITICAL, logger="youtube_downloader.ui.callback")

    class _FakeRoot:
        pass

    root = _FakeRoot()
    install_ui_exception_logging(root)

    try:
        raise ValueError("button broke")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()

    root.report_callback_exception(exc_type, exc_value, exc_tb)

    assert any("callback da interface" in r.message for r in caplog.records)
    assert any(r.levelname == "CRITICAL" for r in caplog.records)
