from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL


def download_mp3(
    url: str,
    output_dir: Path,
    bitrate: int,
    filename: str | None,
) -> Path:
    """Download a YouTube video's audio as an MP3.

    Returns the path of the produced MP3 file. Raises yt_dlp.utils.DownloadError
    on extraction/download failure and OSError on filesystem issues.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is not None:
        safe_name = filename.replace("/", "_").replace("\\", "_")
        outtmpl = f"{safe_name}.%(ext)s"
        restrict_filenames = False
    else:
        outtmpl = "%(title)s.%(ext)s"
        restrict_filenames = True

    ydl_opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "paths": {"home": str(output_dir)},
        "outtmpl": outtmpl,
        "restrictfilenames": restrict_filenames,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(bitrate),
            }
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        probe = ydl.extract_info(url, download=False)
        if probe is None:
            raise RuntimeError("yt-dlp returned no info for the URL")

        target = Path(ydl.prepare_filename(probe)).with_suffix(".mp3")
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: {target}")

        info = ydl.extract_info(url, download=True)

    if info is None:
        raise RuntimeError("yt-dlp returned no info for the URL")

    requested = info.get("requested_downloads") or []
    if requested:
        path = requested[0].get("filepath")
        if path:
            return Path(path)

    return target
