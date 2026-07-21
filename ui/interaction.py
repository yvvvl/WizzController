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
    """Seguimiento estable de un drag, incluso fuera del control.

    ``local_position`` puede envolver temporalmente al borde contrario cuando el
    puntero abandona un ``GestureDetector`` en Windows. Para evitar saltos:

    * la posición global absoluta, anclada al inicio del gesto, es la fuente
      principal;
    * los delta se usan como respaldo y se prueban tanto como acumulados como
      incrementales, porque distintas capas/versiones de Flet han expuesto ambas
      semánticas;
    * una teletransportación global aislada solo se descarta si un delta coherente
      confirma que fue un frame defectuoso;
    * el punto lógico puede quedar fuera, pero el valor visible siempre se limita
      al borde más cercano. Al volver a entrar, continúa sin saltos.

    La clase no importa Flet y por eso se puede probar con eventos simples que
    expongan ``local_position``, ``global_position``, ``local_delta`` y
    ``global_delta``.
    """

    _WRAP_JUMP = 0.72
    _GLOBAL_GLITCH_JUMP = 1.65
    _COHERENT_DELTA_JUMP = 0.65
    _SOURCE_DISAGREEMENT = 0.90

    def __init__(self, width: float, height: float) -> None:
        self.width = max(1.0, float(width))
        self.height = max(1.0, float(height))
        self._anchor_local: tuple[float, float] | None = None
        self._anchor_global: tuple[float, float] | None = None
        self._last: tuple[float, float] | None = None
        self._last_raw: tuple[float, float] | None = None

    @property
    def active(self) -> bool:
        return self._anchor_local is not None

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
        # Fuera de un gesto no necesitamos conservar coordenadas crudas fuera
        # del control. Durante un drag sí: son las que permiten reingresar suave.
        if not self.active and self._last_raw is not None:
            self._last_raw = self._clamp(*self._last_raw)

    def _clamp(self, x: float, y: float) -> tuple[float, float]:
        return (
            max(0.0, min(self.width - 1.0, float(x))),
            max(0.0, min(self.height - 1.0, float(y))),
        )

    def _distance(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        dx = (float(a[0]) - float(b[0])) / max(1.0, self.width)
        dy = (float(a[1]) - float(b[1])) / max(1.0, self.height)
        return (dx * dx + dy * dy) ** 0.5

    def _finish_point(self, raw: tuple[float, float]) -> tuple[float, float]:
        self._last_raw = (float(raw[0]), float(raw[1]))
        self._last = self._clamp(*self._last_raw)
        return self._last

    def begin(self, event: Any) -> tuple[float, float] | None:
        local = self._point(getattr(event, "local_position", None))
        global_pos = self._point(getattr(event, "global_position", None))
        if local is None:
            return None
        local = self._clamp(*local)
        self._anchor_local = local
        self._anchor_global = global_pos
        self._last_raw = local
        self._last = local
        return local

    def tap(self, event: Any) -> tuple[float, float] | None:
        local = self._point(getattr(event, "local_position", None))
        if local is None:
            return None
        self._clear_anchor()
        return self._finish_point(local)

    def _delta_candidates(self, event: Any) -> list[tuple[float, float]]:
        if self._anchor_local is None:
            return []

        reference = self._last_raw or self._anchor_local
        candidates: list[tuple[float, float]] = []
        for attr in ("global_delta", "local_delta"):
            delta = self._point(getattr(event, attr, None))
            if delta is None:
                continue

            # Hipótesis 1: Flet entrega desplazamiento acumulado desde el inicio.
            candidates.append(
                (
                    self._anchor_local[0] + delta[0],
                    self._anchor_local[1] + delta[1],
                )
            )
            # Hipótesis 2: el backend entrega delta desde el frame anterior.
            candidates.append(
                (
                    reference[0] + delta[0],
                    reference[1] + delta[1],
                )
            )

        unique: list[tuple[float, float]] = []
        for candidate in candidates:
            if not any(self._distance(candidate, existing) < 0.0001 for existing in unique):
                unique.append(candidate)
        return unique

    def _closest(
        self,
        candidates: list[tuple[float, float]],
        reference: tuple[float, float],
    ) -> tuple[float, float] | None:
        if not candidates:
            return None
        ranked = sorted(
            candidates,
            key=lambda candidate: self._distance(candidate, reference),
        )
        # Si una interpretación acumulada queda exactamente inmóvil pero la
        # interpretación incremental avanza una distancia razonable, el evento
        # nuevo representa movimiento y conviene usar la segunda.
        if self._distance(ranked[0], reference) < 0.0001:
            moving = [
                candidate
                for candidate in ranked[1:]
                if 0.0001 < self._distance(candidate, reference) <= 0.50
            ]
            if moving:
                return moving[0]
        return ranked[0]

    def move(self, event: Any) -> tuple[float, float] | None:
        if self._anchor_local is None:
            local = self._point(getattr(event, "local_position", None))
            if local is not None:
                return self._finish_point(local)
            return self._last

        reference = self._last_raw or self._anchor_local
        delta_candidates = self._delta_candidates(event)
        closest_delta = self._closest(delta_candidates, reference)

        global_pos = self._point(getattr(event, "global_position", None))
        global_candidate: tuple[float, float] | None = None
        if self._anchor_global is not None and global_pos is not None:
            global_candidate = (
                self._anchor_local[0] + (global_pos[0] - self._anchor_global[0]),
                self._anchor_local[1] + (global_pos[1] - self._anchor_global[1]),
            )

        if global_candidate is not None:
            chosen = global_candidate
            if closest_delta is not None:
                global_jump = self._distance(global_candidate, reference)
                delta_jump = self._distance(closest_delta, reference)
                disagreement = self._distance(global_candidate, closest_delta)
                # Rechaza solo una teletransportación global claramente aislada.
                # Un movimiento real rápido tendrá un delta grande/coincidente.
                if (
                    global_jump > self._GLOBAL_GLITCH_JUMP
                    and delta_jump < self._COHERENT_DELTA_JUMP
                    and disagreement > self._SOURCE_DISAGREEMENT
                ):
                    chosen = closest_delta
            return self._finish_point(chosen)

        local = self._point(getattr(event, "local_position", None))
        if local is not None:
            local_jump = self._distance(local, reference)
            if closest_delta is not None:
                delta_outside = (
                    closest_delta[0] < 0.0
                    or closest_delta[0] > self.width - 1.0
                    or closest_delta[1] < 0.0
                    or closest_delta[1] > self.height - 1.0
                )
                local_on_edge = (
                    local[0] <= 0.0
                    or local[0] >= self.width - 1.0
                    or local[1] <= 0.0
                    or local[1] >= self.height - 1.0
                )
                # Al salir del detector, algunos frames informan exactamente
                # (0, 0) o el borde opuesto. Si el delta demuestra que el
                # puntero siguió hacia fuera, conservar esa trayectoria.
                if (
                    local_on_edge
                    and delta_outside
                    and self._distance(local, closest_delta) > self._WRAP_JUMP
                ):
                    return self._finish_point(closest_delta)
            if local_jump > self._WRAP_JUMP:
                if closest_delta is not None and self._distance(closest_delta, reference) < local_jump:
                    return self._finish_point(closest_delta)
                if not delta_candidates:
                    # Sin evidencia de un recorrido real completo, mantener el
                    # último punto evita el flash al borde opuesto.
                    return self._last
            return self._finish_point(local)

        if closest_delta is not None:
            return self._finish_point(closest_delta)
        return self._last

    def end(self, event: Any) -> tuple[float, float] | None:
        point = self.move(event)
        self._clear_anchor()
        return point

    def cancel(self) -> tuple[float, float] | None:
        point = self._last if self.active else None
        self._clear_anchor()
        return point

    def _clear_anchor(self) -> None:
        self._anchor_local = None
        self._anchor_global = None
