from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VoicePerformanceGovernor:
    """Gobernador liviano para escucha continua.

    Objetivo: mantener el punto dulce entre latencia y consumo sin bajar modelo,
    sin recortar comandos y sin quitar funcionalidades.

    No decide comandos. Solo decide pausas/cadencia y reduce trabajo inútil en
    ciclos de silencio/no-wake/alucinación.
    """

    non_wake_streak: int = 0
    silence_streak: int = 0
    hallucination_streak: int = 0
    last_command_at: float = 0.0
    last_wake_at: float = 0.0
    last_activity_at: float = field(default_factory=time.time)
    latency_ewma: float = 0.0

    def reset(self) -> None:
        self.non_wake_streak = 0
        self.silence_streak = 0
        self.hallucination_streak = 0
        self.last_activity_at = time.time()

    def observe_silence(self) -> None:
        self.silence_streak = min(20, self.silence_streak + 1)
        self.non_wake_streak = max(0, self.non_wake_streak - 1)

    def observe_non_wake(self) -> None:
        self.non_wake_streak = min(12, self.non_wake_streak + 1)
        self.silence_streak = 0
        self.last_activity_at = time.time()

    def observe_hallucination(self) -> None:
        self.hallucination_streak = min(8, self.hallucination_streak + 1)
        self.non_wake_streak = min(12, self.non_wake_streak + 2)
        self.silence_streak = 0
        self.last_activity_at = time.time()

    def observe_wake(self) -> None:
        self.last_wake_at = time.time()
        self.non_wake_streak = 0
        self.silence_streak = 0
        self.hallucination_streak = max(0, self.hallucination_streak - 1)
        self.last_activity_at = time.time()

    def observe_command(self, elapsed: float | None = None) -> None:
        self.last_command_at = time.time()
        self.non_wake_streak = 0
        self.silence_streak = 0
        self.hallucination_streak = 0
        self.last_activity_at = time.time()
        if elapsed is not None:
            try:
                e = float(elapsed)
                self.latency_ewma = e if self.latency_ewma <= 0 else (self.latency_ewma * 0.72 + e * 0.28)
            except Exception:
                pass

    def idle_pause_seconds(self, cfg: dict[str, Any]) -> float:
        """Pausa entre ciclos sin voz.

        Arranca rápido para sentirse disponible. Si pasan muchos silencios
        seguidos, descansa más para no gastar CPU en loops inútiles.
        """
        if not bool(cfg.get("adaptive_governor_enabled", True)):
            return max(0.05, int(cfg.get("continuous_idle_sleep_ms", 280)) / 1000.0)
        min_ms = int(cfg.get("governor_idle_min_ms", 70))
        max_ms = int(cfg.get("governor_idle_max_ms", 260))
        base = int(cfg.get("continuous_idle_sleep_ms", 120))
        # Después de un comando o wake reciente, vuelve a escuchar rápido.
        recent = time.time() - max(self.last_command_at, self.last_wake_at)
        if recent < 2.0:
            return max(0.05, min_ms / 1000.0)
        ms = base + min(260, self.silence_streak * 22)
        # Phase 43: CPU saver de silencio estable. Solo actúa cuando hay varios
        # ciclos limpios sin voz; ante wake/comando reciente vuelve al modo rápido.
        try:
            if bool(cfg.get("continuous_idle_cpu_saver_enabled", False)):
                start_streak = int(cfg.get("continuous_silence_idle_start_streak", 999))
                if self.silence_streak >= start_streak:
                    ms += min(260, int(cfg.get("continuous_silence_idle_extra_ms", 0)))
        except Exception:
            pass
        return max(0.05, min(max_ms, max(min_ms, ms)) / 1000.0)

    def non_wake_pause_seconds(self, cfg: dict[str, Any]) -> float:
        """Pausa tras transcripción válida pero sin activador.

        Debe ser corta para no sentirse lento, pero aumenta si hay muchas frases
        de fondo sin activador.
        """
        if not bool(cfg.get("adaptive_governor_enabled", True)):
            base_ms = int(cfg.get("continuous_pause_after_non_wake_ms", 180))
            return max(0.08, min(0.90, base_ms / 1000.0))
        min_ms = int(cfg.get("governor_non_wake_min_ms", 120))
        max_ms = int(cfg.get("governor_non_wake_max_ms", 380))
        base = int(cfg.get("continuous_pause_after_non_wake_ms", 120))
        ms = base + min(440, max(0, self.non_wake_streak - 1) * 55)
        if self.hallucination_streak:
            ms += min(240, self.hallucination_streak * 45)
        return max(0.08, min(max_ms, max(min_ms, ms)) / 1000.0)

    def after_command_pause_seconds(self, cfg: dict[str, Any], ok: bool = True) -> float:
        min_ms = int(cfg.get("governor_after_command_min_ms", 100))
        base = int(cfg.get("continuous_pause_after_command_ms", 180 if ok else 140))
        return max(0.08, min(0.65, max(min_ms, base) / 1000.0))

    def snapshot(self) -> dict[str, Any]:
        return {
            "non_wake_streak": self.non_wake_streak,
            "silence_streak": self.silence_streak,
            "hallucination_streak": self.hallucination_streak,
            "latency_ewma": round(self.latency_ewma, 3),
            "last_command_age": round(time.time() - self.last_command_at, 2) if self.last_command_at else None,
        }
