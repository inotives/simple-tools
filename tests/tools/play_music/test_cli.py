from pathlib import Path

import pytest
from typer.testing import CliRunner

from simple_tools.cli import app
from simple_tools.tools.play_music import cli as pm_cli

runner = CliRunner()


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()


def test_root_help_lists_play_music() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "play-music" in result.output


def test_play_music_help_shows_all_flags() -> None:
    result = runner.invoke(app, ["play-music", "--help"])
    assert result.exit_code == 0
    for flag in ("--once", "--no-recursive", "--debug"):
        assert flag in result.output


def test_play_music_missing_folder_exits_one(tmp_path: Path) -> None:
    result = runner.invoke(app, ["play-music", str(tmp_path / "nope")])
    assert result.exit_code == 1
    assert "play-music:" in result.output


def test_play_music_empty_folder_exits_one(tmp_path: Path) -> None:
    result = runner.invoke(app, ["play-music", str(tmp_path)])
    assert result.exit_code == 1
    assert "no .mp3 files found" in result.output


def test_play_music_once_plays_each_track_exactly_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ("a.mp3", "b.mp3", "c.mp3"):
        _touch(tmp_path / name)

    plays: list[Path] = []

    def fake_play_one(path: Path) -> int:
        plays.append(path)
        return 0

    monkeypatch.setattr(pm_cli, "play_one", fake_play_one)

    result = runner.invoke(app, ["play-music", str(tmp_path), "--once"])

    assert result.exit_code == 0
    assert {p.name for p in plays} == {"a.mp3", "b.mp3", "c.mp3"}
    assert len(plays) == 3


def test_play_music_default_loops_until_interrupted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ("a.mp3", "b.mp3"):
        _touch(tmp_path / name)

    counter = {"n": 0}

    def fake_play_one(path: Path) -> int:
        del path
        counter["n"] += 1
        if counter["n"] > 5:
            raise KeyboardInterrupt
        return 0

    monkeypatch.setattr(pm_cli, "play_one", fake_play_one)

    result = runner.invoke(app, ["play-music", str(tmp_path)])

    assert result.exit_code == 0
    assert counter["n"] >= 5  # crossed at least one full pass and started another


def test_play_music_missing_ffplay_exits_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _touch(tmp_path / "song.mp3")

    def fake_play_one(_: Path) -> int:
        raise FileNotFoundError("ffplay")

    monkeypatch.setattr(pm_cli, "play_one", fake_play_one)

    result = runner.invoke(app, ["play-music", str(tmp_path)])

    assert result.exit_code == 1
    assert "ffplay not found" in result.output
    assert "brew install ffmpeg" in result.output


def test_play_music_no_recursive_skips_subdirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _touch(tmp_path / "top.mp3")
    _touch(tmp_path / "sub" / "deep.mp3")

    plays: list[Path] = []

    def fake_play_one(path: Path) -> int:
        plays.append(path)
        return 0

    monkeypatch.setattr(pm_cli, "play_one", fake_play_one)

    result = runner.invoke(
        app, ["play-music", str(tmp_path), "--once", "--no-recursive"]
    )

    assert result.exit_code == 0
    assert {p.name for p in plays} == {"top.mp3"}


def test_play_music_does_not_repeat_track_across_pass_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reshuffling between passes must not put the just-played track first."""
    a = tmp_path / "a.mp3"
    b = tmp_path / "b.mp3"
    a.touch()
    b.touch()

    # Force pass 1 = [b, a] (last_played ends as `a`), pass 2 raw = [a, b]
    # (which would replay `a` immediately without the boundary fix).
    shuffle_outputs = iter([[b, a], [a, b], [b, a]])

    def fake_shuffle(lst: list[Path]) -> None:
        lst[:] = next(shuffle_outputs)

    monkeypatch.setattr(pm_cli.random, "shuffle", fake_shuffle)

    plays: list[str] = []

    def fake_play_one(path: Path) -> int:
        plays.append(path.name)
        if len(plays) >= 4:
            raise KeyboardInterrupt
        return 0

    monkeypatch.setattr(pm_cli, "play_one", fake_play_one)

    result = runner.invoke(app, ["play-music", str(tmp_path)])

    assert result.exit_code == 0
    assert len(plays) == 4
    for i in range(1, len(plays)):
        assert plays[i] != plays[i - 1], (
            f"back-to-back repeat at index {i}: {plays}"
        )


def test_play_music_debug_reraises_missing_ffplay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _touch(tmp_path / "song.mp3")

    def fake_play_one(_: Path) -> int:
        raise FileNotFoundError("ffplay")

    monkeypatch.setattr(pm_cli, "play_one", fake_play_one)

    result = runner.invoke(app, ["play-music", str(tmp_path), "--debug"])

    assert result.exit_code != 0
    assert isinstance(result.exception, FileNotFoundError)
