from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner
from yt_dlp.utils import DownloadError

from simple_tools.cli import app
from simple_tools.tools.yt_mp3 import cli as yt_cli

runner = CliRunner()


def test_root_help_lists_yt_mp3() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "yt-mp3" in result.output


def test_yt_mp3_help_shows_all_flags() -> None:
    result = runner.invoke(app, ["yt-mp3", "--help"])
    assert result.exit_code == 0
    for flag in ("--output", "--bitrate", "--filename", "--debug"):
        assert flag in result.output


def test_yt_mp3_missing_url_exits_non_zero() -> None:
    result = runner.invoke(app, ["yt-mp3"])
    assert result.exit_code != 0


def test_yt_mp3_success_prints_resolved_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "out" / "video.mp3"

    def fake_download(url: str, output_dir: Path, bitrate: int, filename: Any) -> Path:
        del url, bitrate, filename
        output_dir.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        return target

    monkeypatch.setattr(yt_cli, "download_mp3", fake_download)
    result = runner.invoke(
        app, ["yt-mp3", "https://example.com/v", "-o", str(tmp_path / "out")]
    )
    assert result.exit_code == 0
    assert str(target.resolve()) in result.output


def test_yt_mp3_download_error_exits_one(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(*_: Any, **__: Any) -> Path:
        raise DownloadError("network is sad")

    monkeypatch.setattr(yt_cli, "download_mp3", fake_download)
    result = runner.invoke(app, ["yt-mp3", "https://bad.example/v"])
    assert result.exit_code == 1
    assert "yt-mp3:" in result.output
    assert "network is sad" in result.output


def test_yt_mp3_existing_file_refusal_exits_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_download(*_: Any, **__: Any) -> Path:
        raise FileExistsError("Refusing to overwrite existing file: x.mp3")

    monkeypatch.setattr(yt_cli, "download_mp3", fake_download)
    result = runner.invoke(app, ["yt-mp3", "https://example.com/v"])
    assert result.exit_code == 1
    assert "Refusing to overwrite" in result.output


def test_yt_mp3_debug_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(*_: Any, **__: Any) -> Path:
        raise DownloadError("boom")

    monkeypatch.setattr(yt_cli, "download_mp3", fake_download)
    result = runner.invoke(app, ["yt-mp3", "https://example.com/v", "--debug"])
    assert result.exit_code != 0
    assert isinstance(result.exception, DownloadError)
