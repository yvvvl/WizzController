from __future__ import annotations

import re
import unicodedata
from typing import Any

from .base_manager import JsonManager


# Ya no bloqueamos palabras como pc/pese. Se permiten, pero con prefijo estricto.
# Solo limpiamos tokens absurdamente comunes/de una letra que causarían activaciones accidentales.
DANGEROUS_SINGLE_TOKENS = {
    "a", "e", "i", "o", "u", "y", "de", "la", "el", "los", "las", "un", "una",
    "si", "se", "no", "ok", "ya", "eh", "ah", "mm", "mhm",
}


def _normalize_keyword(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value or ""))
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9ñ\s_-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


class VoiceConfigManager(JsonManager):
    """Configuración persistente del sistema de voz.

    Fase 27:
    - mantiene captura frase completa con activador + comando;
    - agrega puente de pausa natural tras activador: "pc" + pausa corta + comando;
    - deja activadores editables como pc/pese, siempre al inicio.
    """

    DEFAULTS: dict[str, Any] = {
        "enabled": False,
        "mode": "push_to_talk",
        "language": "es",
        "language_mode": "es_mixed",  # es_mixed | es | auto_ptt

        # Push-to-talk: mejor precisión porque se activa manualmente.
        "model_size": "base",
        "device": "cpu",
        "compute_type": "int8",
        "cpu_threads": 2,
        "num_workers": 1,

        # Segundo plano: punto dulce. Modelo base con 1 hilo entiende mejor sin comerse CPU.
        "performance_profile": "balanced",
        "voice_setup_preset": "adaptive",
        "continuous_strategy": "wake_then_command",

        # Perfil de entrada de micrófono. Voicemeeter/noise gate corta a cero
        # entre palabras; por eso necesita margen de silencio y pre-roll.
        # Valores: normal | flow_gated | gated | very_gated | far_field | adaptive | far_field | adaptive.
        # flow_gated es el punto dulce para hablar de corrido: "pc apaga la luz".
        "audio_input_profile": "adaptive",
        # Phase 41: soporte de voz lejana sin subir hilos/modelo.
        # Normalización local del WAV: solo se activa en presets/perfiles de distancia.
        "voice_capture_input_gain": 1.0,
        "voice_capture_normalize_target_rms": 0.0,
        "voice_capture_normalize_max_gain": 1.0,
        "continuous_model_size": "base",
        "continuous_compute_type": "int8",
        "continuous_cpu_threads": 1,
        "continuous_num_workers": 1,
        "continuous_vad_filter": False,
        "unload_model_when_continuous_stops": False,

        "record_seconds": 4.0,
        "continuous_record_seconds": 3.0,
        "sample_rate": 16000,
        "channels": 1,
        "vad_filter": True,
        "smart_recording": True,
        "end_silence_ms": 850,
        "start_timeout": 2.0,
        "continuous_start_timeout": 1.25,
        "continuous_idle_sleep_ms": 120,
        "continuous_error_sleep_ms": 700,
        "continuous_pause_after_command_ms": 160,
        "continuous_pause_after_non_wake_ms": 140,
        "continuous_require_wake_word": True,
        "strict_wake_default": True,
        "continuous_force_strict_wake": True,
        "continuous_wake_position": "prefix",
        "continuous_require_command_after_wake": True,
        "wake_words": ["pc", "pese", "wizz", "wiz"],

        # Wake probe. Si el clip es demasiado corto, NO se transcribe: se trata como
        # posible wake y se escucha el comando. Esto evita alucinaciones tipo "el truco...".
        "wake_probe_seconds": 3.8,
        "wake_probe_start_timeout": 1.25,
        "wake_probe_min_speech_seconds": 0.30,
        "wake_probe_end_silence_ms": 900,
        # Si el usuario dice "pc" y pausa ~1s antes del comando, no cortes
        # la captura inmediatamente. Solo se aplica cuando el habla inicial fue corta.
        "wake_command_bridge_ms": 1550,
        "wake_command_bridge_short_max_seconds": 1.10,
        "command_pause_bridge_ms": 950,
        "command_pause_bridge_short_max_seconds": 0.85,
        "wake_probe_min_rms_peak": 0.075,
        "wake_min_transcribe_seconds": 0.48,
        # Fase 26: el fallback de activador corto generaba falsos wake con ruido/Voicemeeter.
        # Default OFF: se prefiere capturar activador + comando completo en una sola toma.
        "wake_short_candidate_enabled": False,
        "wake_short_candidate_min_seconds": 0.35,
        "wake_short_candidate_max_seconds": 0.55,
        "wake_short_candidate_min_rms_peak": 0.060,
        "continuous_hallucination_pause_ms": 140,
        "continuous_hide_hallucinated_text": True,

        # Si solo escuchó el activador, escucha el comando después.
        "command_after_wake_seconds": 3.4,
        "command_after_wake_start_timeout": 1.25,
        "command_after_wake_end_silence_ms": 900,
        "command_after_wake_min_speech_seconds": 0.30,

        # Pausas cortas: no queremos 7-10s de bloqueo después de un falso no-wake.
        "adaptive_non_wake_backoff": False,
        "non_wake_backoff_step_ms": 150,
        "non_wake_backoff_max_ms": 350,

        "min_record_seconds": 0.55,
        "continuous_min_speech_seconds": 0.34,
        "continuous_min_rms_peak": 0.004,
        "energy_threshold": 0.004,
        "beam_size": 1,
        "continuous_beam_size": 1,
        "initial_prompt": "Comandos cortos de domótica en español chileno mezclado con inglés. Activadores posibles al inicio: wizz, wiz, pc, pese. No inventes texto repetido. Ejemplos: pc apaga la luz, pese prende la luz al cincuenta, wizz pon rojo al cien, wiz turn on red at fifty.",
        "cooldown_ms": 320,
        "confirm_low_confidence": False,
        "min_confidence": 0.62,

        # Fase 22: protección multi-voz liviana. No es biometría fuerte: es
        # un filtro local para evitar que cualquier voz con activador ejecute.
        # open = cualquiera con activador, cautious = si hay perfil verifica;
        # owner = requiere perfil vocal entrenado.
        "speaker_security_mode": "open",
        "speaker_min_similarity": 0.58,
        "speaker_verify_continuous_only": True,
        "speaker_enroll_seconds": 2.8,
        "speaker_enroll_phrase": "pc prende la luz al cincuenta",


        # Phase 39: punto dulce de performance.
        # Precargar modelo de fondo evita que el primer comando tarde demasiado.
        # Bajar prioridad del hilo de voz evita tirones sin sacrificar precisión.
        "continuous_warm_model": True,
        "continuous_background_thread_low_priority": True,
        "performance_governor_enabled": True,

        # Phase 40: gobernador adaptativo de recursos.
        # Mantiene precisión/funciones, pero evita loops inútiles en silencio/no-wake.
        "adaptive_governor_enabled": True,
        "governor_idle_min_ms": 120,
        "governor_idle_max_ms": 520,
        "governor_non_wake_min_ms": 120,
        "governor_non_wake_max_ms": 680,
        "governor_after_command_min_ms": 100,
        "continuous_emit_transcribing_events": False,
        "continuous_emit_idle_events": False,
        "voice_governor_diagnostics": False,
        # Phase 42: micrófono adaptativo cerca/lejos.
        # Mantiene base+1 hilo, pero ajusta VAD/normalización para no requerir cambiar presets.
        "auto_mic_adaptation_enabled": True,
        "auto_mic_distance_mode": "adaptive",
        "voice_capture_input_gain": 1.15,
        "voice_capture_normalize_target_rms": 0.050,
        "voice_capture_normalize_max_gain": 2.4,
        # Phase 43: ahorro de CPU en reposo sin bajar modelo ni comandos.
        # Reduce callbacks de audio y baja cadencia solo cuando hay silencio real.
        "continuous_audio_block_ms": 40,
        "continuous_idle_cpu_saver_enabled": False,
        "continuous_silence_idle_extra_ms": 0,
        "continuous_silence_idle_start_streak": 999,
        "continuous_min_execute_confidence": 0.78,
        "continuous_color_requires_action_word": True,
        "continuous_strip_repeated_wake_words": True,
        # Phase 46: respuesta tras silencio + guardas de segundo plano.
        "continuous_reject_repeated_wake_only": True,
        "continuous_reject_short_color_fuzzy": True,
        "history_limit": 25,
    }

    def __init__(self) -> None:
        super().__init__("voice_config.json", default_data=dict(self.DEFAULTS))
        if not isinstance(self.data, dict):
            self.data = dict(self.DEFAULTS)
        changed = self._ensure_defaults_and_migrate()
        if changed:
            self.save()

    @staticmethod
    def sanitize_wake_words(words: Any) -> list[str]:
        if isinstance(words, str):
            items = [w.strip() for w in words.split(",") if w.strip()]
        elif isinstance(words, list):
            items = [str(w).strip() for w in words if str(w).strip()]
        else:
            items = []
        cleaned: list[str] = []
        for item in items:
            w = _normalize_keyword(item)
            if not w or w in DANGEROUS_SINGLE_TOKENS:
                continue
            # Permitimos pc/pese/wiz aunque sean cortos. Bloqueamos solo activadores de 1 char.
            if len(w.replace(" ", "")) < 2:
                continue
            if w not in cleaned:
                cleaned.append(w)
        return cleaned or ["wizz", "wiz"]

    def _ensure_defaults_and_migrate(self) -> bool:
        changed = False
        for key, value in self.DEFAULTS.items():
            if key not in self.data:
                self.data[key] = value
                changed = True

        if self.data.get("performance_profile") == "gaming":
            self.data["performance_profile"] = "balanced"
            changed = True

        # Segundo plano sigue con prefijo estricto: evita ejecutar conversaciones normales.
        if self.data.get("continuous_require_wake_word") is not True:
            self.data["continuous_require_wake_word"] = True
            changed = True
        if self.data.get("continuous_force_strict_wake") is not True:
            self.data["continuous_force_strict_wake"] = True
            changed = True
        if self.data.get("continuous_wake_position") != "prefix":
            self.data["continuous_wake_position"] = "prefix"
            changed = True

        cleaned = self.sanitize_wake_words(self.data.get("wake_words"))
        if cleaned != self.data.get("wake_words"):
            self.data["wake_words"] = cleaned
            changed = True

        # Migraciones desde fase 19: conservar que el usuario pueda agregar pc/pese,
        # bajar pausas y evitar clips wake alucinados.
        minimums = {
            "wake_probe_seconds": 2.20,
            "wake_probe_min_speech_seconds": 0.34,
            "wake_probe_end_silence_ms": 650,
            "wake_command_bridge_ms": 1100,
            "wake_command_bridge_short_max_seconds": 0.90,
            "command_pause_bridge_ms": 650,
            "wake_min_transcribe_seconds": 0.35,
            "wake_short_candidate_min_seconds": 0.20,
            "wake_short_candidate_max_seconds": 0.50,
            "continuous_pause_after_non_wake_ms": 150,
            "non_wake_backoff_max_ms": 600,
            "energy_threshold": 0.004,
            "continuous_min_rms_peak": 0.004,
        }
        for key, min_value in minimums.items():
            try:
                cur = float(self.data.get(key, 0))
            except Exception:
                cur = 0
            if cur < float(min_value):
                self.data[key] = min_value
                changed = True

        # Limitar pausas excesivas que quedaron en JSON de fases previas.
        maximums = {
            "continuous_pause_after_non_wake_ms": 350,
            "non_wake_backoff_max_ms": 350,
            "wake_probe_start_timeout": 1.80,
            "command_after_wake_start_timeout": 1.60,
            "continuous_pause_after_command_ms": 350,
            "wake_probe_end_silence_ms": 1150,
            "command_after_wake_end_silence_ms": 1150,
            "wake_command_bridge_ms": 1800,
            "command_pause_bridge_ms": 1200,
        }
        for key, max_value in maximums.items():
            try:
                cur = float(self.data.get(key, max_value))
            except Exception:
                cur = max_value
            if cur > float(max_value):
                self.data[key] = max_value
                changed = True

        # Fase 26: no activar por ruido corto. Si más adelante se quiere un modo
        # wake-word dedicado, debe ser con detector real, no con este fallback.
        if self.data.get("wake_short_candidate_enabled") is not False:
            self.data["wake_short_candidate_enabled"] = False
            changed = True

        if self.data.get("language_mode") not in ("es_mixed", "es", "auto_ptt"):
            self.data["language_mode"] = "es_mixed"
            changed = True
        if not self.data.get("continuous_strategy"):
            self.data["continuous_strategy"] = "wake_then_command"
            changed = True

        return changed

    def get_config(self) -> dict[str, Any]:
        if isinstance(self.data, dict):
            changed = self._ensure_defaults_and_migrate()
            if changed:
                self.save()
        out = dict(self.DEFAULTS)
        if isinstance(self.data, dict):
            out.update(self.data)
        out["wake_words"] = self.sanitize_wake_words(out.get("wake_words"))
        out["continuous_require_wake_word"] = True
        out["continuous_force_strict_wake"] = True
        out["continuous_wake_position"] = "prefix"
        # Opciones base siempre activas: se prioriza estabilidad y latencia baja.
        out["smart_recording"] = True
        out["vad_filter"] = True
        out["wake_short_candidate_enabled"] = False
        # Umbral anti-alucinación sin comerse habla normal.
        # Fase 29: 0.055 era demasiado alto para micros con Voicemeeter/compresión
        # y obligaba a hablar muy marcado. Usamos umbral según perfil.
        try:
            profile = str(out.get("audio_input_profile", "flow_gated") or "flow_gated")
            floor = 0.012 if profile == "very_gated" else 0.009
            out["wake_probe_min_rms_peak"] = max(float(out.get("wake_probe_min_rms_peak", floor)), floor)
            out["continuous_min_rms_peak"] = max(float(out.get("continuous_min_rms_peak", floor)), floor)
        except Exception:
            out["wake_probe_min_rms_peak"] = 0.009
            out["continuous_min_rms_peak"] = 0.009
        try:
            out["wake_command_bridge_ms"] = max(1000, min(1800, int(out.get("wake_command_bridge_ms", 1450))))
            out["command_pause_bridge_ms"] = max(500, min(1200, int(out.get("command_pause_bridge_ms", 900))))
            out["wake_command_bridge_short_max_seconds"] = max(0.75, min(1.35, float(out.get("wake_command_bridge_short_max_seconds", 1.10))))
        except Exception:
            out["wake_command_bridge_ms"] = 1450
            out["command_pause_bridge_ms"] = 900
            out["wake_command_bridge_short_max_seconds"] = 1.10
        return out

    def set_value(self, key: str, value: Any) -> None:
        if not isinstance(self.data, dict):
            self.data = dict(self.DEFAULTS)
        self.data[key] = value
        self._ensure_defaults_and_migrate()
        self.save()

    def update_config(self, **kwargs: Any) -> None:
        if not isinstance(self.data, dict):
            self.data = dict(self.DEFAULTS)
        if "wake_words" in kwargs:
            kwargs["wake_words"] = self.sanitize_wake_words(kwargs.get("wake_words"))
        kwargs["continuous_require_wake_word"] = True
        kwargs["continuous_force_strict_wake"] = True
        kwargs["continuous_wake_position"] = "prefix"
        kwargs["smart_recording"] = True
        kwargs["vad_filter"] = True
        self.data.update(kwargs)
        self._ensure_defaults_and_migrate()
        self.save()
