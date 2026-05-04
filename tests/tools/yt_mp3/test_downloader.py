from pathlib import Path
from typing import Any

import pytest

from simple_tools.tools.yt_mp3 import downloader
from simple_tools.tools.yt_mp3.downloader import download_mp3


class FakeYDL:
    """Stand-in for yt_dlp.YoutubeDL that touches a fake output file."""

    instances: list["FakeYDL"] = []
    title = "test_video"

    def __init__(self, opts: dict[str, Any]) -> None:
        self.opts = opts
        FakeYDL.instances.append(self)

    def __enter__(self) -> "FakeYDL":
        return self

    def __exit__(self, *_: object) -> bool:
        return False

    def prepare_filename(self, info: dict[str, Any]) -> str:
        home = Path(self.opts["paths"]["home"])
        return str(home / f"{info['title']}.webm")

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        del url
        if not download:
            return {"title": self.title}
        target = Path(self.opts["paths"]["home"]) / f"{self.title}.mp3"
        target.touch()
        return {
            "title": self.title,
            "requested_downloads": [{"filepath": str(target)}],
        }


@pytest.fixture(autouse=True)
def _reset_fake() -> None:
    FakeYDL.instances.clear()


@pytest.fixture
def patched_ydl(monkeypatch: pytest.MonkeyPatch) -> type[FakeYDL]:
    monkeypatch.setattr(downloader, "YoutubeDL", FakeYDL)
    return FakeYDL


def test_creates_output_dir_and_returns_path(
    patched_ydl: type[FakeYDL], tmp_path: Path
) -> None:
    output_dir = tmp_path / "out"
    result = download_mp3("https://example.com/v", output_dir, 192, None)

    assert output_dir.is_dir()
    assert result == output_dir / "test_video.mp3"
    assert result.exists()


def test_passes_bitrate_to_postprocessor(
    patched_ydl: type[FakeYDL], tmp_path: Path
) -> None:
    download_mp3("https://example.com/v", tmp_path / "out", 320, None)

    opts = patched_ydl.instances[0].opts
    pp = opts["postprocessors"][0]
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "320"


def test_uses_custom_filename(patched_ydl: type[FakeYDL], tmp_path: Path) -> None:
    download_mp3("https://example.com/v", tmp_path / "out", 192, "my-clip")

    opts = patched_ydl.instances[0].opts
    assert opts["outtmpl"] == "my-clip.%(ext)s"
    assert opts["restrictfilenames"] is False


def test_filename_strips_path_separators(
    patched_ydl: type[FakeYDL], tmp_path: Path
) -> None:
    download_mp3("https://example.com/v", tmp_path / "out", 192, "evil/../name")

    opts = patched_ydl.instances[0].opts
    assert "/" not in opts["outtmpl"]
    assert "\\" not in opts["outtmpl"]


def test_refuses_to_overwrite_existing_file(
    patched_ydl: type[FakeYDL], tmp_path: Path
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "test_video.mp3").touch()

    with pytest.raises(FileExistsError):
        download_mp3("https://example.com/v", output_dir, 192, None)
