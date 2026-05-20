"""Application logging to rotating files next to the executable."""

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

from youtube_downloader.config import get_project_root

LOG_DIR = get_project_root() / "logs"
LOG_CACHE_DIR = LOG_DIR / "cache"
APP_LOG = LOG_DIR / "app.log"
ERROR_LOG = LOG_DIR / "errors.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 5


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT)
    root = logging.getLogger("youtube_downloader")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    app_handler = RotatingFileHandler(
        APP_LOG,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        ERROR_LOG,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    root.addHandler(app_handler)
    root.addHandler(error_handler)

    logging.getLogger("PIL").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"youtube_downloader.{name}")


def clear_preview_cache() -> None:
    for path in LOG_CACHE_DIR.glob("preview_*.jpg"):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def install_exception_hooks() -> None:
    logger = get_logger("unhandled")

    def handle_exception(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical(
            "Exceção não tratada na thread principal",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = handle_exception

    def handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        thread_name = args.thread.name if args.thread else "?"
        logger.critical(
            "Exceção não tratada na thread %s",
            thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = handle_thread_exception


def install_ui_exception_logging(root: object) -> None:
    """Log Tk/CustomTkinter callback exceptions to app.log and errors.log.

    Without this, errors in button/command handlers only appear on stderr
    (e.g. "Exception in Tkinter callback") and are easy to miss when debugging.
    """
    logger = get_logger("ui.callback")

    def report_callback_exception(exc, val, tb) -> None:
        logger.critical(
            "Exceção em callback da interface",
            exc_info=(exc, val, tb),
        )

    setattr(root, "report_callback_exception", report_callback_exception)
