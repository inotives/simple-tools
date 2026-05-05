import os
import random
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import IO

_BARS = 32
_BLOCKS = " ▁▂▃▄▅▆▇█"
_LEVELS = len(_BLOCKS) - 1
_BAR_FRAME_INTERVAL = 0.08
_TIMER_ONLY_INTERVAL = 0.25
_BEAT_PROBABILITY = 0.04
_CLEAR_WIDTH = _BARS + 32  # bars + timer + padding

# VU-meter palette: green (calm) → yellow (mid) → red (peak/beats).
_COLOR_GREEN = "\033[92m"
_COLOR_YELLOW = "\033[93m"
_COLOR_RED = "\033[91m"
_COLOR_RESET = "\033[0m"


def _color_for(level: int) -> str:
    if level >= 6:
        return _COLOR_RED
    if level >= 4:
        return _COLOR_YELLOW
    return _COLOR_GREEN


def _format_time(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def _step(heights: list[float], rng: random.Random) -> list[float]:
    """Random-walk each bar height, with occasional 'beat' spikes."""
    out: list[float] = []
    for h in heights:
        delta = rng.gauss(0, 1.4)
        if rng.random() < _BEAT_PROBABILITY:
            delta += rng.uniform(2.5, 5.0)
        new_h = max(0.0, min(float(_LEVELS), h + delta))
        out.append(new_h)
    return out


@contextmanager
def visualizer(
    duration: float | None = None,
    show_bars: bool = False,
    stream: IO[str] | None = None,
) -> Iterator[None]:
    """Render an updating playback line for the duration of the context.

    Always shows an elapsed/total timer. Bars are opt-in via show_bars.
    No-ops on non-TTY streams (safe in pipes, tests, CI).
    """
    out = stream if stream is not None else sys.stderr
    if not out.isatty():
        yield
        return

    stop = threading.Event()
    rng = random.Random()
    interval = _BAR_FRAME_INTERVAL if show_bars else _TIMER_ONLY_INTERVAL
    start = time.monotonic()
    use_color = "NO_COLOR" not in os.environ

    def _render(heights: list[float]) -> str:
        elapsed = time.monotonic() - start
        if duration is not None:
            timer = f"[{_format_time(elapsed)}/{_format_time(duration)}]"
        else:
            timer = f"[{_format_time(elapsed)}]"
        if show_bars:
            if use_color:
                bars = "".join(
                    _color_for(int(h)) + _BLOCKS[int(h)] for h in heights
                ) + _COLOR_RESET
            else:
                bars = "".join(_BLOCKS[int(h)] for h in heights)
            return f"  {timer}  {bars}"
        return f"  {timer}"

    def _loop() -> None:
        heights = [rng.uniform(0.0, float(_LEVELS)) for _ in range(_BARS)]
        while not stop.is_set():
            if show_bars:
                heights = _step(heights, rng)
            out.write(f"\r{_render(heights)}")
            out.flush()
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1.0)
        out.write("\r" + " " * _CLEAR_WIDTH + "\r")
        out.flush()
