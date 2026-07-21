from __future__ import annotations

import time
from typing import Any


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


class LocalEditGuard:
    """Evita que sync externo pise un slider mientras el usuario lo arrastra.

    El bug típico era:
      UI slider -> setPilot fire-and-forget -> getPilot viejo/lag -> sync_state
      pisa el valor local -> el thumb salta 40/20/60.

    Este guard no retrasa el envío; solo bloquea escrituras de UI externas durante
    una ventana corta. Si el valor entrante ya coincide, no bloquea nada.
    """

    def __init__(self, hold_seconds: float = 0.95) -> None:
        self.hold_seconds = float(hold_seconds)
        self.until = 0.0
        self.value: Any = None

    def touch(self, value: Any = None, *, hold_seconds: float | None = None) -> None:
        self.value = value
        self.until = time.monotonic() + float(self.hold_seconds if hold_seconds is None else hold_seconds)

    def active(self) -> bool:
        return time.monotonic() < self.until

    def blocks(self, incoming: Any = None, *, tolerance: float = 0.0) -> bool:
        if not self.active():
            return False
        if incoming is None or self.value is None:
            return True
        try:
            # números simples
            if abs(float(incoming) - float(self.value)) <= float(tolerance):
                return False
        except Exception:
            pass
        try:
            # tuplas/listas RGB
            if isinstance(incoming, (list, tuple)) and isinstance(self.value, (list, tuple)):
                if len(incoming) == len(self.value):
                    diffs = [abs(float(a) - float(b)) for a, b in zip(incoming, self.value)]
                    if all(d <= float(tolerance) for d in diffs):
                        return False
        except Exception:
            pass
        return incoming != self.value


class DragPositionTracker:
    """Reconstruye coordenadas de drag sin confiar ciegamente en local_position.

    En desktop, algunos eventos de borde pueden reportar por un frame una
    ``local_position`` del lado opuesto (por ejemplo x=0 al llegar al borde
    derecho). El desplazamiento global no sufre ese wrap, así que anclamos el
    drag al par local/global inicial y lo usamos como fuente principal.

    La clase no depende de Flet: acepta cualquier evento con atributos
    ``local_position``, ``global_position`` y opcionalmente ``local_delta``.
    """

    def __init__(self, width: float, height: float) -> None:
        self.width = max(1.0, float(width))
        self.height = max(1.0, float(height))
        self._anchor_local: tuple[float, float] | None = None
        self._anchor_global: tuple[float, float] | None = None
        self._last: tuple[float, float] | None = None

    @staticmethod
    def _point(value: Any) -> tuple[float, float] | None:
        if value is None:
            return None
        try:
            return float(value.x), float(value.y)
        except Exception:
            pass
        try:
            return float(value[0]), float(value[1])
        except Exception:
            return None

    def resize(self, width: float, height: float) -> None:
        self.width = max(1.0, float(width))
        self.height = max(1.0, float(height))
        if self._last is not None:
            self._last = self._clamp(*self._last)

    def _clamp(self, x: float, y: float) -> tuple[float, float]:
        return (
            max(0.0, min(self.width - 1.0, float(x))),
            max(0.0, min(self.height - 1.0, float(y))),
        )

    def begin(self, event: Any) -> tuple[float, float] | None:
        local = self._point(getattr(event, "local_position", None))
        global_pos = self._point(getattr(event, "global_position", None))
        if local is None:
            return None
        local = self._clamp(*local)
        self._anchor_local = local
        self._anchor_global = global_pos
        self._last = local
        return local

    def tap(self, event: Any) -> tuple[float, float] | None:
        local = self._point(getattr(event, "local_position", None))
        if local is None:
            return None
        self.cancel()
        self._last = self._clamp(*local)
        return self._last

    def move(self, event: Any) -> tuple[float, float] | None:
        if self._anchor_local is None:
            local = self._point(getattr(event, "local_position", None))
            if local is not None:
                self._last = self._clamp(*local)
            return self._last

        candidates: list[tuple[float, float]] = []

        # En Flet 0.85.2 los delta de drag representan el desplazamiento desde
        # el inicio del gesto. Son la fuente más estable al llegar al borde.
        global_delta = self._point(getattr(event, "global_delta", None))
        if global_delta is not None:
            candidates.append((self._anchor_local[0] + global_delta[0], self._anchor_local[1] + global_delta[1]))

        global_pos = self._point(getattr(event, "global_position", None))
        if self._anchor_global is not None and global_pos is not None:
            candidates.append(
                (
                    self._anchor_local[0] + (global_pos[0] - self._anchor_global[0]),
                    self._anchor_local[1] + (global_pos[1] - self._anchor_global[1]),
                )
            )

        local_delta = self._point(getattr(event, "local_delta", None))
        if local_delta is not None:
            candidates.append((self._anchor_local[0] + local_delta[0], self._anchor_local[1] + local_delta[1]))

        if candidates:
            # Si dos fuentes discrepan por un wrap de borde, elegimos la que
            # conserva mejor la continuidad con el último frame. En un drag
            # real rápido los delta global/local coinciden, por lo que no se
            # penaliza atravesar el picker de punta a punta.
            if self._last is not None and len(candidates) > 1:
                def continuity(candidate: tuple[float, float]) -> float:
                    return abs(candidate[0] - self._last[0]) / self.width + abs(candidate[1] - self._last[1]) / self.height

                spread_x = max(c[0] for c in candidates) - min(c[0] for c in candidates)
                spread_y = max(c[1] for c in candidates) - min(c[1] for c in candidates)
                if spread_x > self.width * 0.45 or spread_y > self.height * 0.45:
                    point = min(candidates, key=continuity)
                else:
                    point = candidates[0]
            else:
                point = candidates[0]
            self._last = self._clamp(*point)
            return self._last

        local = self._point(getattr(event, "local_position", None))
        if local is not None:
            # Último fallback. Solo se usa cuando Flet no entregó ninguna
            # coordenada acumulada/global.
            candidate = self._clamp(*local)
            if self._last is not None:
                wrapped_x = abs(candidate[0] - self._last[0]) > self.width * 0.75
                wrapped_y = abs(candidate[1] - self._last[1]) > self.height * 0.75
                if wrapped_x or wrapped_y:
                    return self._last
            self._last = candidate
            return self._last
        return self._last

    def end(self, event: Any) -> tuple[float, float] | None:
        point = self.move(event)
        self._anchor_local = None
        self._anchor_global = None
        return point

    def cancel(self) -> None:
        self._anchor_local = None
        self._anchor_global = None
