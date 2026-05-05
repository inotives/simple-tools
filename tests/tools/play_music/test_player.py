from pathlib import Path
from typing import Any

import pytest

from simple_tools.tools.play_music import player
from simple_tools.tools.play_music.player import find_mp3s, play_one


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()


def test_find_mp3s_recursive_collects_nested(tmp_path: Path) -> None:
    _touch(tmp_path / "a.mp3")
    _touch(tmp_path / "sub" / "b.mp3")
    _touch(tmp_path / "sub" / "deep" / "c.mp3")

    found = find_mp3s(tmp_path, recursive=True)

    assert found == sorted(found)
    assert {p.name for p in found} == {"a.mp3", "b.mp3", "c.mp3"}


def test_find_mp3s_non_recursive_skips_subdirs(tmp_path: Path) -> None:
    _touch(tmp_path / "a.mp3")
    _touch(tmp_path / "sub" / "b.mp3")

    found = find_mp3s(tmp_path, recursive=False)

    assert {p.name for p in found} == {"a.mp3"}


def test_find_mp3s_extension_match_is_case_insensitive(tmp_path: Path) -> None:
    _touch(tmp_path / "lower.mp3")
    _touch(tmp_path / "UPPER.MP3")
    _touch(tmp_path / "Mixed.Mp3")

    found = find_mp3s(tmp_path, recursive=False)

    assert {p.name for p in found} == {"lower.mp3", "UPPER.MP3", "Mixed.Mp3"}


def test_find_mp3s_ignores_non_mp3(tmp_path: Path) -> None:
    _touch(tmp_path / "song.mp3")
    _touch(tmp_path / "cover.jpg")
    _touch(tmp_path / "notes.txt")
    _touch(tmp_path / "song.wav")

    found = find_mp3s(tmp_path, recursive=False)

    assert {p.name for p in found} == {"song.mp3"}


def test_find_mp3s_missing_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_mp3s(tmp_path / "nope", recursive=False)


def test_play_one_invokes_ffplay_with_expected_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    class FakeCompleted:
        returncode = 0

    def fake_run(cmd: list[str], check: bool = False) -> FakeCompleted:
        captured["cmd"] = cmd
        captured["check"] = check
        return FakeCompleted()

    monkeypatch.setattr(player.subprocess, "run", fake_run)

    track = tmp_path / "song.mp3"
    track.touch()
    rc = play_one(track)

    assert rc == 0
    assert captured["cmd"][0] == "ffplay"
    assert "-nodisp" in captured["cmd"]
    assert "-autoexit" in captured["cmd"]
    assert captured["cmd"][-1] == str(track)
    assert captured["check"] is False


def test_play_one_propagates_missing_ffplay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(*_: Any, **__: Any) -> Any:
        raise FileNotFoundError("ffplay")

    monkeypatch.setattr(player.subprocess, "run", fake_run)

    with pytest.raises(FileNotFoundError):
        play_one(tmp_path / "song.mp3")


def test_play_one_returns_nonzero_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakeCompleted:
        returncode = 130

    def fake_run(*_: Any, **__: Any) -> FakeCompleted:
        return FakeCompleted()

    monkeypatch.setattr(player.subprocess, "run", fake_run)

    assert play_one(tmp_path / "song.mp3") == 130
