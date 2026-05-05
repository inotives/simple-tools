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
