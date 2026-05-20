"""Desktop notifications when a download finishes (optional, from settings)."""

import subprocess
import sys

from youtube_downloader.core.logging_config import get_logger

logger = get_logger("notifications")


def notify_download_complete(title: str, message: str) -> None:
    """Best-effort notification; never raises."""
    try:
        if sys.platform == "linux":
            subprocess.run(
                ["notify-send", title, message, "-a", "YouTube Downloader"],
                check=False,
            )
        elif sys.platform == "darwin":
            safe_title = title.replace('"', '\\"')
            safe_message = message.replace('"', '\\"')
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{safe_message}" with title "{safe_title}"',
                ],
                check=False,
            )
        elif sys.platform == "win32":
            _notify_windows(title, message)
        else:
            logger.debug("Notificacao ignorada: plataforma nao suportada")
    except OSError as exc:
        logger.warning("Falha ao exibir notificacao: %s", exc)


def _notify_windows(title: str, message: str) -> None:
    safe_title = title.replace("'", "''")
    safe_message = message.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(5000, '{safe_title}', '{safe_message}', "
        "[System.Windows.Forms.ToolTipIcon]::Info); "
        "Start-Sleep -Milliseconds 600; "
        "$n.Dispose()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
    )
