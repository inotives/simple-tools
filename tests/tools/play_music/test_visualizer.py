import io

import pytest

from simple_tools.tools.play_music.visualizer import visualizer


class _FakeTTY(io.StringIO):
    """StringIO that pretends to be a TTY so the visualizer thread starts."""

    def isatty(self) -> bool:
        return True


def test_visualizer_noop_when_not_a_tty() -> None:
    """A plain StringIO is non-TTY; the context should yield without writing."""
    buf = io.StringIO()
    with visualizer(stream=buf):
        pass
    assert buf.getvalue() == ""


def test_visualizer_renders_timer_only_by_default() -> None:
    """Without show_bars, the visualizer renders a [mm:ss] timer and no blocks."""
    import time

    buf = _FakeTTY()
    with visualizer(duration=None, show_bars=False, stream=buf):
        time.sleep(0.05)  # > _TIMER_ONLY_INTERVAL (0.25)
    out = buf.getvalue()

    assert "[00:00]" in out
    assert not any(ch in out for ch in "▁▂▃▄▅▆▇█")
    assert out.endswith("\r")


def test_visualizer_renders_elapsed_over_total_when_duration_known() -> None:
    """With duration, the timer reads `[mm:ss/mm:ss]`."""
    import time

    buf = _FakeTTY()
    with visualizer(duration=225.0, show_bars=False, stream=buf):
        time.sleep(0.05)
    out = buf.getvalue()

    assert "[00:00/03:45]" in out


def test_visualizer_renders_bars_when_show_bars_true() -> None:
    """With show_bars, frames carry block characters AND the timer."""
    import time

    buf = _FakeTTY()
    with visualizer(duration=60.0, show_bars=True, stream=buf):
        time.sleep(0.05)  # first frame writes before the loop sleeps
    out = buf.getvalue()

    assert any(ch in out for ch in "▁▂▃▄▅▆▇█")
    assert "[00:00/01:00]" in out
    assert out.endswith("\r")


def test_visualizer_emits_color_codes_with_bars_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ANSI color escapes are present in bar frames unless NO_COLOR is set."""
    import time

    monkeypatch.delenv("NO_COLOR", raising=False)
    buf = _FakeTTY()
    with visualizer(duration=60.0, show_bars=True, stream=buf):
        time.sleep(0.05)
    out = buf.getvalue()

    # at least one of green/yellow/red and the reset code
    assert any(code in out for code in ("\033[92m", "\033[93m", "\033[91m"))
    assert "\033[0m" in out


def test_visualizer_omits_color_when_NO_COLOR_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """NO_COLOR opts out of ANSI color codes while keeping bars and timer."""
    import time

    monkeypatch.setenv("NO_COLOR", "1")
    buf = _FakeTTY()
    with visualizer(duration=60.0, show_bars=True, stream=buf):
        time.sleep(0.05)
    out = buf.getvalue()

    assert any(ch in out for ch in "▁▂▃▄▅▆▇█")
    for code in ("\033[92m", "\033[93m", "\033[91m", "\033[0m"):
        assert code not in out


def test_visualizer_no_color_codes_in_timer_only_mode() -> None:
    """Timer-only mode never emits color codes."""
    import time

    buf = _FakeTTY()
    with visualizer(duration=None, show_bars=False, stream=buf):
        time.sleep(0.05)
    out = buf.getvalue()

    for code in ("\033[92m", "\033[93m", "\033[91m", "\033[0m"):
        assert code not in out
