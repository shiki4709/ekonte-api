"""Optional CLI/Python adapter; the HTTP server accepts uploads only."""

from pathlib import Path
from urllib.parse import urlparse


def download(url: str, directory: Path) -> Path:
    host = (urlparse(url).hostname or "").lower()
    if urlparse(url).scheme != "https" or not any(
        host == h or host.endswith("." + h) for h in ("tiktok.com", "instagram.com")
    ):
        raise ValueError("URL adapter accepts HTTPS TikTok and Instagram links only")
    import yt_dlp

    with yt_dlp.YoutubeDL(
        {
            "format": "best[height<=720]/best",
            "noplaylist": True,
            "outtmpl": str(directory / "reference.%(ext)s"),
            "quiet": True,
            "socket_timeout": 30,
            "retries": 2,
            "max_filesize": 100 * 1024 * 1024,
            "match_filter": yt_dlp.utils.match_filter_func("duration <= 180"),
        }
    ) as client:
        info = client.extract_info(url, download=True)
        if not info:
            raise ValueError("video was unavailable or exceeded the download limits")
        path = Path(client.prepare_filename(info))
    if not path.is_file():
        raise ValueError("video download did not produce a file")
    return path
