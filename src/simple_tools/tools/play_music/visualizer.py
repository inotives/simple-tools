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
_FRAME_INTERVAL = 0.08
_BEAT_PROBABILITY = 0.04


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
def visualizer(stream: IO[str] | None = None) -> Iterator[None]:
    """Render a single-line animated bar visualizer for the duration of the context.

    Silently no-ops when the stream is not a TTY (e.g. when piped or under test),
    so wrapping a code path in `visualizer()` is safe in any environment.
    """
    out = stream if stream is not None else sys.stderr
    if not out.isatty():
        yield
        return

    stop = threading.Event()
    rng = random.Random()

    def _loop() -> None:
        heights = [rng.uniform(0.0, float(_LEVELS)) for _ in range(_BARS)]
        while not stop.is_set():
            heights = _step(heights, rng)
            line = "".join(_BLOCKS[int(h)] for h in heights)
            out.write(f"\r  {line}")
            out.flush()
            time.sleep(_FRAME_INTERVAL)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1.0)
        out.write("\r" + " " * (_BARS + 2) + "\r")
        out.flush()
