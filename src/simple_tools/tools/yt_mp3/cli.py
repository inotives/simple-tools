from pathlib import Path
from typing import Annotated

import typer
from yt_dlp.utils import DownloadError

from simple_tools.tools.yt_mp3.downloader import download_mp3


def yt_mp3(
    url: Annotated[
        str,
        typer.Argument(
            help=(
                "YouTube video URL to extract audio from "
                "(e.g. https://www.youtube.com/watch?v=...). Playlists and "
                "channel URLs are not supported."
            ),
            show_default=False,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Directory to write the MP3 into. Created automatically if it "
                "does not exist. Resolved relative to the current working "
                "directory."
            ),
        ),
    ] = Path("output/yt-mp3"),
    bitrate: Annotated[
        int,
        typer.Option(
            "--bitrate",
            "-b",
            help=(
                "MP3 bitrate in kbps. Common values: 128 (compact), 192 "
                "(balanced, default), 320 (highest standard MP3 quality)."
            ),
        ),
    ] = 192,
    filename: Annotated[
        str | None,
        typer.Option(
            "--filename",
            "-f",
            help=(
                "Output filename without extension. The .mp3 extension is "
                "added automatically. Path separators ('/' and '\\\\') are "
                "stripped. If omitted, the video's sanitized title is used."
            ),
            show_default=False,
        ),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help=(
                "On failure, show the full Python traceback instead of a "
                "single-line error message. Useful for diagnosing yt-dlp or "
                "ffmpeg issues."
            ),
        ),
    ] = False,
) -> None:
    """Download a YouTube video's audio as an MP3.

    Fetches the best available audio stream with yt-dlp and re-encodes it to
    MP3 via ffmpeg (which must be installed on PATH; e.g. `brew install
    ffmpeg`). Refuses to overwrite an existing file. On success, prints the
    absolute path of the produced MP3 to stdout; progress and any errors go
    to stderr.
    """
    try:
        result = download_mp3(url, output, bitrate, filename)
    except (DownloadError, OSError, RuntimeError) as exc:
        if debug:
            raise
        typer.echo(f"yt-mp3: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(str(result.resolve()))
