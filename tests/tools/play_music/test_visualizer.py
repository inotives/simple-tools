import io

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


def test_visualizer_writes_frames_when_tty_and_clears_on_exit() -> None:
    """On a fake-TTY stream, frames emit during the context and clear at exit."""
    import time

    buf = _FakeTTY()
    with visualizer(stream=buf):
        time.sleep(0.12)  # ~1.5 frame intervals
    out = buf.getvalue()

    # at least one frame written (carriage-return prefixed)
    assert out.count("\r") >= 2  # at least one frame + one cleanup
    # frames carry block characters from the bar palette
    assert any(ch in out for ch in "▁▂▃▄▅▆▇█")
    # final cleanup writes a clear-line sequence (CR + spaces + CR)
    assert out.endswith("\r")
