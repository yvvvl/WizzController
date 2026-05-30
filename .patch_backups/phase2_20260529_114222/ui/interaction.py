from __future__ import annotations

import time


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class RateGate:
    """Throttle pequeño para eventos densos de UI: sliders, drag, resize."""

    def __init__(self, interval_s: float) -> None:
        self.interval_s = float(interval_s)
        self._last = 0.0

    def ready(self, *, force: bool = False) -> bool:
        if force:
            self._last = time.monotonic()
            return True
        now = time.monotonic()
        if now - self._last >= self.interval_s:
            self._last = now
            return True
        return False

    def reset(self) -> None:
        self._last = 0.0
