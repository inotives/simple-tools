import subprocess
from pathlib import Path


def find_mp3s(folder: Path, recursive: bool) -> list[Path]:
    """Return a sorted list of `.mp3` files under `folder` (case-insensitive).

    Raises FileNotFoundError if `folder` does not exist or is not a directory.
    """
    if not folder.is_dir():
        raise FileNotFoundError(f"Not a directory: {folder}")

    pattern = "**/*" if recursive else "*"
    return sorted(p for p in folder.glob(pattern) if p.is_file() and p.suffix.lower() == ".mp3")


def play_one(path: Path) -> int:
    """Play a single audio file via ffplay (blocking). Returns ffplay's exit code.

    Raises FileNotFoundError if `ffplay` is not on PATH.
    """
    return subprocess.run(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
        check=False,
    ).returncode


def get_duration(path: Path) -> float | None:
    """Return the duration of an audio file in seconds via ffprobe.

    Returns None if ffprobe is unavailable, exits non-zero, or returns
    output that cannot be parsed as a float.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None
