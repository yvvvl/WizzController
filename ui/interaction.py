from __future__ import annotations

import time


class RateGate:
    """Limitador simple para eventos de UI muy frecuentes."""

    def __init__(self, interval: float) -> None:
        self.interval = float(interval)
        self.last = 0.0

    def ready(self, *, force: bool = False) -> bool:
        now = time.monotonic()
        if force or now - self.last >= self.interval:
            self.last = now
            return True
        return False

    def force(self) -> None:
        self.last = 0.0
