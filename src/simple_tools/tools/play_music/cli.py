import random
from pathlib import Path
from typing import Annotated

import typer

from simple_tools.tools.play_music.player import find_mp3s, get_duration, play_one
from simple_tools.tools.play_music.visualizer import visualizer


def play_music(
    folder: Annotated[
        Path,
        typer.Argument(
            help=(
                "Directory to scan for MP3 files. Subdirectories are included "
                "by default; use --no-recursive to scan only the top level."
            ),
            show_default=False,
        ),
    ],
    once: Annotated[
        bool,
        typer.Option(
            "--once",
            help=(
                "Play the shuffled playlist once and exit. Without this flag, "
                "the player loops forever, reshuffling between passes."
            ),
        ),
    ] = False,
    no_recursive: Annotated[
        bool,
        typer.Option(
            "--no-recursive",
            help="Scan only the top level of the folder; do not descend into subfolders.",
        ),
    ] = False,
    visualize: Annotated[
        bool,
        typer.Option(
            "--visualize",
            help=(
                "Render an animated bar visualizer beside the playback timer. "
                "Bars are colored green/yellow/red by height (set NO_COLOR=1 "
                "to disable color). Cosmetic only — the bars are time-driven, "
                "not synced to the actual audio. No-op when stdout is not a TTY."
            ),
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help=(
                "On failure, show the full Python traceback instead of a "
                "single-line error message."
            ),
        ),
    ] = False,
) -> None:
    """Randomly play MP3 files from a folder.

    Discovers MP3s under the given folder, shuffles them, and plays each via
    ffplay (which must be on PATH; e.g. `brew install ffmpeg`). Default mode
    loops forever — press Ctrl-C to stop. Use --once to play one shuffled
    pass and exit. Currently only supports `.mp3`; other audio formats may be
    added in a future release.
    """
    try:
        tracks = find_mp3s(folder, recursive=not no_recursive)
    except FileNotFoundError as exc:
        if debug:
            raise
        typer.echo(f"play-music: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not tracks:
        typer.echo(f"play-music: no .mp3 files found in {folder}", err=True)
        raise typer.Exit(code=1)

    last_played: Path | None = None
    try:
        while True:
            shuffled = list(tracks)
            random.shuffle(shuffled)
            if last_played is not None and len(shuffled) > 1 and shuffled[0] == last_played:
                shuffled[0], shuffled[-1] = shuffled[-1], shuffled[0]
            for track in shuffled:
                duration = get_duration(track)
                if duration is not None:
                    mins, secs = divmod(int(duration), 60)
                    typer.echo(f"▶ {track} ({mins:02d}:{secs:02d})")
                else:
                    typer.echo(f"▶ {track}")
                try:
                    with visualizer(duration=duration, show_bars=visualize):
                        play_one(track)
                except FileNotFoundError as exc:
                    if debug:
                        raise
                    typer.echo(
                        "play-music: ffplay not found on PATH. "
                        "Install ffmpeg (e.g. `brew install ffmpeg`).",
                        err=True,
                    )
                    raise typer.Exit(code=1) from exc
                last_played = track
            if once:
                return
    except KeyboardInterrupt:
        return
