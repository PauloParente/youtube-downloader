"""Reusable styled widgets."""

from youtube_downloader.ui_qt.widgets.buttons import (
    DangerButton,
    GhostButton,
    IconButton,
    LinkButton,
    PrimaryButton,
)
from youtube_downloader.ui_qt.widgets.card import Card
from youtube_downloader.ui_qt.widgets.common import (
    apply_page_margins,
    field_label,
    muted_label,
    secondary_label,
    set_text_class,
)
from youtube_downloader.ui_qt.widgets.compact_media_row import CompactMediaRow
from youtube_downloader.ui_qt.widgets.download_alert import DownloadAlert
from youtube_downloader.ui_qt.widgets.loading_spinner import LoadingSpinner
from youtube_downloader.ui_qt.widgets.download_options_bar import DownloadOptionsBar
from youtube_downloader.ui_qt.widgets.empty_state import EmptyState
from youtube_downloader.ui_qt.widgets.download_progress_strip import DownloadProgressStrip
from youtube_downloader.ui_qt.widgets.media_preview_row import MediaPreviewRow
from youtube_downloader.ui_qt.widgets.page_header import PageHeader
from youtube_downloader.ui_qt.widgets.preview_skeleton import PreviewSkeleton
from youtube_downloader.ui_qt.widgets.section import SectionTitle, Separator
from youtube_downloader.ui_qt.widgets.segmented_control import SegmentedControl
from youtube_downloader.ui_qt.widgets.thumbnail import ThumbnailLabel

__all__ = [
    "Card",
    "CompactMediaRow",
    "DangerButton",
    "EmptyState",
    "DownloadAlert",
    "LoadingSpinner",
    "DownloadOptionsBar",
    "DownloadProgressStrip",
    "GhostButton",
    "IconButton",
    "LinkButton",
    "MediaPreviewRow",
    "PageHeader",
    "PreviewSkeleton",
    "PrimaryButton",
    "SectionTitle",
    "SegmentedControl",
    "Separator",
    "ThumbnailLabel",
    "apply_page_margins",
    "field_label",
    "muted_label",
    "secondary_label",
    "set_text_class",
]
