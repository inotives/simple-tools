from pathlib import Path
from typing import Annotated

import typer
from yt_dlp.utils import DownloadError

from simple_tools.tools.yt_mp3.downloader import download_mp3


def yt_mp3(
    url: Annotated[str, typer.Argument(help="YouTube video URL.")],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory; created if missing.",
        ),
    ] = Path("output/yt-mp3"),
    bitrate: Annotated[
        int,
        typer.Option(
            "--bitrate",
            "-b",
            help="MP3 bitrate in kbps (e.g. 128, 192, 320).",
        ),
    ] = 192,
    filename: Annotated[
        str | None,
        typer.Option(
            "--filename",
            "-f",
            help="Override output filename (without extension). Defaults to the video's sanitized title.",
        ),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Re-raise exceptions instead of printing a one-line error.",
        ),
    ] = False,
) -> None:
    """Download a YouTube video's audio as an MP3."""
    try:
        result = download_mp3(url, output, bitrate, filename)
    except (DownloadError, OSError, RuntimeError) as exc:
        if debug:
            raise
        typer.echo(f"yt-mp3: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(str(result.resolve()))
