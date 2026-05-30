from __future__ import annotations

import gc
import logging
import re
import threading
import time
from typing import Any, Callable

from config.voice_config_manager import VoiceConfigManager
from config.voice_training_manager import VoiceTrainingManager
from config.voice_profile_manager import VoiceProfileManager
from core.voice.audio_input import AudioInput, AudioCaptureResult
from core.voice.intent_parser import VoiceActionRegistry, VoiceIntentParser, normalize_text
from core.voice.transcriber import WhisperTranscriber

_LOG = logging.getLogger(__name__)

VoiceEventCallback = Callable[[dict[str, Any]], None]


class VoiceService:
    """Servicio de voz WizZ.

    Fase 27:
    - Mantiene captura activador + comando, pero tolera pausa natural tras el activador.
    - Evita que decir "pc" y pausar ~1s corte la frase antes del comando.
    - Mantiene activadores editables como pc/pese, siempre al inicio.
    - Push-to-talk mantiene mayor precisión sin dejar CPU ocupada todo el tiempo.
    """

    def __init__(self, wiz) -> None:
        self.wiz = wiz
        self.config_manager = VoiceConfigManager()
        self.training_manager = VoiceTrainingManager()
        self.profile_manager = VoiceProfileManager()
        self.registry = VoiceActionRegistry(wiz)
        self.parser = VoiceIntentParser(wiz)
        self._transcriber_ptt: WhisperTranscriber | None = None
        self._transcriber_continuous: WhisperTranscriber | None = None
        self._last_exec_at = 0.0
        self._continuous_thread: threading.Thread | None = None
        self._continuous_stop = threading.Event()
        self._continuous_callback: VoiceEventCallback | None = None
        self._last_idle_emit = 0.0
        self._non_wake_streak = 0

    # ------------------------------------------------------------------ #
    # Configuración / dependencias
    # ------------------------------------------------------------------ #
    def config(self) -> dict[str, Any]:
        return self.config_manager.get_config()

    def save_config(self, **kwargs: Any) -> None:
        self.config_manager.update_config(**kwargs)
        if any(k in kwargs for k in ("model_size", "device", "compute_type", "cpu_threads", "num_workers")):
            self._transcriber_ptt = None
        if any(k in kwargs for k in ("continuous_model_size", "device", "continuous_compute_type", "continuous_cpu_threads", "continuous_num_workers")):
            self._transcriber_continuous = None

    def apply_performance_profile(self, profile: str) -> dict[str, Any]:
        """Aplica presets de eficiencia general para segundo plano.

        eco: menor impacto general para trabajar/jugar/estudiar.
        balanced: mejor entendimiento manteniendo consumo bajo.
        accuracy: más precisión, más CPU/RAM.
        """
        profile = str(profile or "eco")
        cfg_current = self.config()
        if profile == "gaming":
            profile = "eco"
        if profile == "accuracy":
            payload = {
                "performance_profile": "accuracy",
                "continuous_strategy": "wake_then_command",
                "continuous_model_size": "base",
                "continuous_cpu_threads": 2,
                "continuous_num_workers": 1,
                "continuous_vad_filter": True,
                "continuous_record_seconds": 3.0,
                "continuous_start_timeout": 0.95,
                "continuous_idle_sleep_ms": 260,
                "continuous_pause_after_command_ms": 220,
                "continuous_pause_after_non_wake_ms": 180,
                "continuous_wake_position": "prefix",
                "continuous_require_command_after_wake": True,
                "wake_words": ["wizz", "wiz"],
                "continuous_require_wake_word": True,
                "language_mode": "es_mixed",
                "language": "es",
                "wake_probe_seconds": 3.0,
                "wake_probe_start_timeout": 0.95,
                "wake_probe_min_speech_seconds": 0.42,
                "wake_probe_end_silence_ms": 650,
                "wake_probe_min_rms_peak": 0.010,
                "command_after_wake_seconds": 3.0,
                "command_after_wake_start_timeout": 0.95,
                "continuous_min_speech_seconds": 0.55,
                "continuous_min_rms_peak": 0.060,
                "energy_threshold": 0.012,
                "adaptive_non_wake_backoff": True,
                "non_wake_backoff_max_ms": 700,
                "cooldown_ms": 320,
            }
        elif profile == "balanced":
            payload = {
                "performance_profile": "balanced",
                "continuous_strategy": "wake_then_command",
                "continuous_model_size": "base",
                "continuous_cpu_threads": 1,
                "continuous_num_workers": 1,
                "continuous_vad_filter": False,
                "continuous_record_seconds": 3.0,
                "continuous_start_timeout": 0.95,
                "continuous_idle_sleep_ms": 280,
                "continuous_pause_after_command_ms": 220,
                "continuous_pause_after_non_wake_ms": 180,
                "continuous_wake_position": "prefix",
                "continuous_require_command_after_wake": True,
                "wake_words": ["wizz", "wiz"],
                "continuous_require_wake_word": True,
                "language_mode": "es_mixed",
                "language": "es",
                "wake_probe_seconds": 3.0,
                "wake_probe_start_timeout": 0.95,
                "wake_probe_min_speech_seconds": 0.42,
                "wake_probe_end_silence_ms": 650,
                "wake_probe_min_rms_peak": 0.060,
                "command_after_wake_seconds": 3.0,
                "command_after_wake_start_timeout": 0.95,
                "continuous_min_speech_seconds": 0.55,
                "continuous_min_rms_peak": 0.060,
                "energy_threshold": 0.012,
                "adaptive_non_wake_backoff": True,
                "non_wake_backoff_max_ms": 700,
                "cooldown_ms": 320,
            }
        else:
            payload = {
                "performance_profile": "eco",
                "continuous_strategy": "wake_then_command",
                "continuous_model_size": "base",
                "continuous_cpu_threads": 1,
                "continuous_num_workers": 1,
                "continuous_vad_filter": False,
                "continuous_record_seconds": 2.8,
                "continuous_start_timeout": 1.1,
                "continuous_idle_sleep_ms": 420,
                "continuous_pause_after_command_ms": 260,
                "continuous_pause_after_non_wake_ms": 220,
                "continuous_wake_position": "prefix",
                "continuous_require_command_after_wake": True,
                "wake_words": ["wizz", "wiz"],
                "continuous_require_wake_word": True,
                "language_mode": "es_mixed",
                "language": "es",
                "wake_probe_seconds": 2.8,
                "wake_probe_start_timeout": 1.1,
                "wake_probe_min_speech_seconds": 0.42,
                "wake_probe_end_silence_ms": 650,
                "wake_probe_min_rms_peak": 0.070,
                "command_after_wake_seconds": 3.0,
                "command_after_wake_start_timeout": 0.95,
                "continuous_min_speech_seconds": 0.60,
                "continuous_min_rms_peak": 0.070,
                "energy_threshold": 0.014,
                "adaptive_non_wake_backoff": True,
                "non_wake_backoff_max_ms": 800,
                "cooldown_ms": 350,
            }
        # No pisar activadores personalizados del usuario al cambiar perfil.
        payload["wake_words"] = cfg_current.get("wake_words", payload.get("wake_words", ["wizz", "wiz"]))
        payload["audio_input_profile"] = cfg_current.get("audio_input_profile", payload.get("audio_input_profile", "gated"))
        self.save_config(**payload)
        return payload


    def apply_setup_preset(self, preset: str) -> dict[str, Any]:
        """Preset rápido de micrófono/latencia sin tocar activadores ni seguridad.

        Fase 25: no es un modo nuevo; es una forma segura de mover varios
        parámetros juntos y ver luego en diagnóstico qué está pasando.
        """
        preset = str(preset or "balanced").strip().lower()
        cfg_current = self.config()
        # Base: punto dulce para uso diario.
        payload: dict[str, Any] = {
            "voice_setup_preset": preset,
            "performance_profile": cfg_current.get("performance_profile", "balanced"),
            "continuous_strategy": "wake_then_command",
            "continuous_model_size": cfg_current.get("continuous_model_size", "base"),
            "continuous_cpu_threads": int(cfg_current.get("continuous_cpu_threads", 1) or 1),
            "continuous_num_workers": 1,
            "continuous_require_wake_word": True,
            "continuous_force_strict_wake": True,
            "continuous_wake_position": "prefix",
            "continuous_require_command_after_wake": True,
            "continuous_pause_after_command_ms": 220,
            "continuous_pause_after_non_wake_ms": 180,
            "adaptive_non_wake_backoff": False,
            "wake_words": cfg_current.get("wake_words", ["pc", "pese", "wizz", "wiz"]),
            "language_mode": cfg_current.get("language_mode", "es_mixed"),
            "language": "es",
            "wake_short_candidate_enabled": False,
            "continuous_hide_hallucinated_text": True,
        }
        if preset in ("voicemeeter", "gated", "vm"):
            payload.update({
                "voice_setup_preset": "voicemeeter",
                "audio_input_profile": "gated",
                "energy_threshold": 0.010,
                "end_silence_ms": 900,
                "continuous_start_timeout": 1.45,
                "wake_probe_seconds": 3.6,
                "wake_probe_start_timeout": 1.45,
                "wake_probe_min_speech_seconds": 0.55,
                "wake_probe_end_silence_ms": 950,
                "wake_command_bridge_ms": 1450,
                "wake_command_bridge_short_max_seconds": 1.10,
                "wake_probe_min_rms_peak": 0.010,
                "command_after_wake_seconds": 3.4,
                "command_after_wake_start_timeout": 1.15,
                "command_after_wake_end_silence_ms": 950,
                "command_after_wake_min_speech_seconds": 0.50,
                "continuous_min_speech_seconds": 0.65,
                "continuous_min_rms_peak": 0.010,
            })
        elif preset in ("very_gated", "gate_fuerte"):
            payload.update({
                "voice_setup_preset": "very_gated",
                "audio_input_profile": "very_gated",
                "energy_threshold": 0.009,
                "end_silence_ms": 1100,
                "continuous_start_timeout": 1.80,
                "wake_probe_seconds": 4.0,
                "wake_probe_start_timeout": 1.80,
                "wake_probe_min_speech_seconds": 0.70,
                "wake_probe_end_silence_ms": 1150,
                "wake_command_bridge_ms": 1650,
                "wake_command_bridge_short_max_seconds": 1.20,
                "wake_probe_min_rms_peak": 0.009,
                "command_after_wake_seconds": 3.8,
                "command_after_wake_start_timeout": 1.50,
                "command_after_wake_end_silence_ms": 1150,
                "command_after_wake_min_speech_seconds": 0.65,
                "continuous_min_speech_seconds": 0.75,
                "continuous_min_rms_peak": 0.009,
            })
        elif preset in ("normal", "mic_normal"):
            payload.update({
                "voice_setup_preset": "normal",
                "audio_input_profile": "normal",
                "energy_threshold": 0.012,
                "end_silence_ms": 650,
                "continuous_start_timeout": 1.10,
                "wake_probe_seconds": 3.0,
                "wake_probe_start_timeout": 1.10,
                "wake_probe_min_speech_seconds": 0.42,
                "wake_probe_end_silence_ms": 700,
                "wake_command_bridge_ms": 1200,
                "wake_command_bridge_short_max_seconds": 1.00,
                "wake_probe_min_rms_peak": 0.060,
                "command_after_wake_seconds": 3.0,
                "command_after_wake_start_timeout": 1.10,
                "command_after_wake_end_silence_ms": 750,
                "command_after_wake_min_speech_seconds": 0.42,
                "continuous_min_speech_seconds": 0.50,
                "continuous_min_rms_peak": 0.060,
            })
        elif preset in ("low", "bajo_consumo", "eco"):
            payload.update({
                "voice_setup_preset": "low",
                "performance_profile": "eco",
                "audio_input_profile": cfg_current.get("audio_input_profile", "gated"),
                "continuous_model_size": "tiny",
                "continuous_cpu_threads": 1,
                "energy_threshold": 0.014,
                "continuous_idle_sleep_ms": 430,
                "continuous_pause_after_non_wake_ms": 260,
                "wake_probe_min_rms_peak": 0.014,
                "continuous_min_rms_peak": 0.014,
            })
        elif preset in ("precision", "preciso", "accuracy"):
            payload.update({
                "voice_setup_preset": "precision",
                "performance_profile": "accuracy",
                "audio_input_profile": cfg_current.get("audio_input_profile", "gated"),
                "continuous_model_size": "base",
                "continuous_cpu_threads": 2,
                "energy_threshold": 0.009,
                "wake_probe_min_rms_peak": 0.009,
                "continuous_min_rms_peak": 0.009,
                "wake_probe_end_silence_ms": 1000,
                "command_after_wake_end_silence_ms": 1000,
            })
        else:
            payload.update({
                "voice_setup_preset": "balanced",
                "audio_input_profile": cfg_current.get("audio_input_profile", "gated"),
                "performance_profile": "balanced",
                "continuous_model_size": "base",
                "continuous_cpu_threads": 1,
            })
        self.save_config(**payload)
        return payload

    def diagnostic_lines(self, result: dict[str, Any]) -> list[str]:
        """Explicación corta de por qué se ejecutó o falló una escucha."""
        if not isinstance(result, dict):
            return ["Sin diagnóstico disponible."]
        lines: list[str] = []
        event = str(result.get("event") or result.get("stage") or result.get("source") or "resultado")
        msg = str(result.get("message") or "")
        text = str(result.get("transcript") or result.get("command_transcript") or "").strip()
        ok = bool(result.get("ok"))
        if ok and result.get("action"):
            lines.append("Acción reconocida y enviada al controlador WiZ.")
        elif "No detecté voz" in msg or result.get("speech_started") is False:
            lines.append("No hubo voz suficiente sobre el umbral. Sube sensibilidad o baja Gate/Denoiser.")
        elif event == "wake_ignored" or "palabra clave" in msg.lower() or "activador" in msg.lower():
            lines.append("Se ignoró por activador: la frase debe empezar por una palabra clave configurada.")
        elif "cooldown" in msg.lower():
            lines.append("Se ignoró por cooldown: llegó demasiado cerca del comando anterior.")
        elif "comando" in msg.lower() and "no" in msg.lower():
            lines.append("El audio pasó el activador, pero el parser no reconoció una acción clara.")
        elif not ok:
            lines.append("No se ejecutó. Revisa texto reconocido, nivel de voz y activador.")

        if result.get("capture_seconds") is not None:
            try:
                sec = float(result.get("capture_seconds") or 0)
                if sec < 0.60:
                    lines.append(f"Audio muy corto ({sec:.2f}s): posible corte por Gate/Voicemeeter.")
                elif sec > 3.8:
                    lines.append(f"Audio largo ({sec:.2f}s): puede aumentar latencia; baja duración o corte silencio.")
                else:
                    lines.append(f"Audio capturado OK: {sec:.2f}s.")
            except Exception:
                pass
        if result.get("rms_peak") is not None:
            try:
                peak = float(result.get("rms_peak") or 0)
                if peak < 0.010:
                    lines.append(f"Nivel bajo ({peak:.4f}): sube ganancia o sensibilidad.")
                elif peak > 0.85:
                    lines.append(f"Nivel muy alto ({peak:.4f}): posible saturación del micrófono.")
                else:
                    lines.append(f"Nivel de voz razonable: {peak:.4f}.")
            except Exception:
                pass
        if result.get("elapsed") is not None:
            try:
                elapsed = float(result.get("elapsed") or 0)
                if elapsed > 5.0:
                    lines.append(f"Latencia alta ({elapsed:.2f}s): baja a perfil equilibrado/normal o revisa modelo cargado.")
                elif elapsed > 2.8:
                    lines.append(f"Latencia media ({elapsed:.2f}s): aceptable, pero optimizable.")
                else:
                    lines.append(f"Latencia buena: {elapsed:.2f}s.")
            except Exception:
                pass
        if result.get("speaker_similarity") is not None:
            lines.append(f"Coincidencia de voz: {result.get('speaker_similarity')} ({result.get('speaker_mode', 'open')}).")
        if text:
            # Detectar transcripciones repetitivas/alucinadas aunque hayan pasado al UI.
            words = normalize_text(text).split()
            if len(words) >= 12 and len(set(words)) <= max(3, len(words) // 5):
                lines.append("Texto repetitivo detectado: probable alucinación de ASR por ruido/clip corto.")
        return lines[:7] or ["Resultado normal. Sin alertas claras."]

    def dependency_status(self) -> dict[str, Any]:
        audio_ok = True
        audio_msg = "audio disponible"
        try:
            import numpy  # type: ignore  # noqa: F401
            import sounddevice  # type: ignore  # noqa: F401
        except Exception as exc:
            audio_ok = False
            audio_msg = f"faltan sounddevice/numpy: {exc}"
        whisper_ok, whisper_msg = WhisperTranscriber.dependency_status()
        return {
            "ok": audio_ok and whisper_ok,
            "audio_ok": audio_ok,
            "whisper_ok": whisper_ok,
            "audio": audio_msg,
            "whisper": whisper_msg,
        }

    # ------------------------------------------------------------------ #
    # Perfil vocal / protección multi-voz
    # ------------------------------------------------------------------ #
    def speaker_status(self) -> dict[str, Any]:
        return self.profile_manager.status()

    def clear_speaker_profile(self) -> dict[str, Any]:
        self.profile_manager.clear()
        return self.profile_manager.status()

    def set_speaker_profile_enabled(self, enabled: bool) -> dict[str, Any]:
        self.profile_manager.set_enabled(enabled)
        return self.profile_manager.status()

    def enroll_speaker_sample(self) -> dict[str, Any]:
        """Graba una muestra corta para entrenar la voz del dueño.

        Solo usa audio local. No sube nada a internet. La muestra se convierte a
        una huella numérica barata y el WAV temporal se elimina.
        """
        cfg = self.config()
        audio = AudioInput(sample_rate=int(cfg.get("sample_rate", 16000)), channels=int(cfg.get("channels", 1)))
        capture = audio.record_smart_to_wav(
            float(cfg.get("speaker_enroll_seconds", 2.8)),
            min_seconds=0.75,
            start_timeout=2.0,
            end_silence_ms=900,
            energy_threshold=float(cfg.get("energy_threshold", 0.010)),
            keep_silence_wav=True,
        )
        if not capture.speech_started or not capture.wav_path:
            return {
                "ok": False,
                "message": "No detecté voz para entrenar",
                "capture_seconds": round(capture.seconds, 2),
                "rms_peak": round(float(capture.rms_peak), 4),
                **self.profile_manager.status(),
            }
        try:
            status = self.profile_manager.add_sample_from_wav(capture.wav_path)
            return {
                "ok": True,
                "message": f"Muestra guardada ({status.get('sample_count')} total)",
                "capture_seconds": round(capture.seconds, 2),
                "rms_peak": round(float(capture.rms_peak), 4),
                **status,
            }
        finally:
            try:
                import os
                os.unlink(capture.wav_path)
            except Exception:
                pass

    def _speaker_policy(self) -> str:
        return str(self.config().get("speaker_security_mode", "open") or "open")

    def _verify_speaker_capture(self, capture: AudioCaptureResult | None) -> dict[str, Any]:
        cfg = self.config()
        mode = self._speaker_policy()
        status = self.profile_manager.status()
        if mode == "open":
            return {"ok": True, "mode": mode, "message": "Voz libre"}
        if bool(cfg.get("speaker_verify_continuous_only", True)) is False:
            pass
        if not status.get("trained") or not status.get("enabled"):
            if mode == "owner":
                return {"ok": False, "mode": mode, "similarity": None, "message": "Perfil vocal no entrenado"}
            return {"ok": True, "mode": mode, "similarity": None, "message": "Sin perfil vocal; permitido"}
        if not capture or not getattr(capture, "wav_path", ""):
            if mode == "owner":
                return {"ok": False, "mode": mode, "similarity": None, "message": "No hay audio para verificar voz"}
            return {"ok": True, "mode": mode, "similarity": None, "message": "Sin audio para verificar; permitido"}
        sim = self.profile_manager.similarity_to_wav(capture.wav_path)
        try:
            import os
            os.unlink(capture.wav_path)
        except Exception:
            pass
        threshold = float(cfg.get("speaker_min_similarity", 0.58))
        if sim is None:
            if mode == "owner":
                return {"ok": False, "mode": mode, "similarity": None, "message": "No pude verificar tu voz"}
            return {"ok": True, "mode": mode, "similarity": None, "message": "Verificación no disponible; permitido"}
        ok = sim >= threshold
        if ok:
            return {"ok": True, "mode": mode, "similarity": round(sim, 3), "message": "Voz verificada"}
        if mode == "cautious":
            # En modo cauteloso no ejecuta si hay perfil y no coincide. Es el
            # balance recomendado cuando hay más gente cerca.
            return {"ok": False, "mode": mode, "similarity": round(sim, 3), "message": "Voz distinta o dudosa"}
        return {"ok": False, "mode": mode, "similarity": round(sim, 3), "message": "Comando ignorado: no parece tu voz"}

    def _audio_profile_overrides(self, cfg: dict[str, Any]) -> dict[str, float | int]:
        """Ajustes por tipo de micrófono.

        Fase 29:
        - "flow_gated" es el punto dulce para Voicemeeter cuando el usuario
          habla de corrido: "pc apaga la luz".
        - Aumenta pre-roll y evita que el VAD corte por micro-pausas del gate.
        - No sube hilos ni modelo: mejora captura, no consumo.
        """
        profile = str(cfg.get("audio_input_profile", "flow_gated") or "flow_gated")
        if profile == "very_gated":
            return {
                "start_timeout": 1.80,
                "wake_end_silence_ms": 1200,
                "cmd_end_silence_ms": 1150,
                "min_speech": 0.62,
                "wake_seconds": 4.0,
                "cmd_seconds": 3.8,
                "pre_roll_ms": 950,
                "wake_bridge_ms": int(cfg.get("wake_command_bridge_ms", 1650)),
                "wake_bridge_short_max": float(cfg.get("wake_command_bridge_short_max_seconds", 1.25)),
            }
        if profile == "normal":
            return {
                "start_timeout": 1.00,
                "wake_end_silence_ms": 700,
                "cmd_end_silence_ms": 750,
                "min_speech": 0.38,
                "wake_seconds": 3.0,
                "cmd_seconds": 3.0,
                "pre_roll_ms": 300,
                "wake_bridge_ms": int(cfg.get("wake_command_bridge_ms", 950)),
                "wake_bridge_short_max": float(cfg.get("wake_command_bridge_short_max_seconds", 0.90)),
            }
        if profile == "gated":
            return {
                "start_timeout": 1.35,
                "wake_end_silence_ms": 950,
                "cmd_end_silence_ms": 950,
                "min_speech": 0.50,
                "wake_seconds": 3.6,
                "cmd_seconds": 3.4,
                "pre_roll_ms": 720,
                "wake_bridge_ms": int(cfg.get("wake_command_bridge_ms", 1450)),
                "wake_bridge_short_max": float(cfg.get("wake_command_bridge_short_max_seconds", 1.10)),
            }
        # flow_gated / voicemeeter_fluido: recomendado para decir todo de corrido.
        return {
            "start_timeout": 1.25,
            "wake_end_silence_ms": 900,
            "cmd_end_silence_ms": 900,
            "min_speech": 0.42,
            "wake_seconds": 3.8,
            "cmd_seconds": 3.4,
            "pre_roll_ms": 850,
            "wake_bridge_ms": int(cfg.get("wake_command_bridge_ms", 1350)),
            "wake_bridge_short_max": float(cfg.get("wake_command_bridge_short_max_seconds", 1.15)),
        }

    def _make_transcriber(self, *, continuous: bool = False) -> WhisperTranscriber:
        cfg = self.config()
        if continuous:
            return WhisperTranscriber(
                model_size=str(cfg.get("continuous_model_size", "tiny")),
                device=str(cfg.get("device", "cpu")),
                compute_type=str(cfg.get("continuous_compute_type", cfg.get("compute_type", "int8"))),
                cpu_threads=int(cfg.get("continuous_cpu_threads", 1)),
                num_workers=int(cfg.get("continuous_num_workers", 1)),
            )
        return WhisperTranscriber(
            model_size=str(cfg.get("model_size", "base")),
            device=str(cfg.get("device", "cpu")),
            compute_type=str(cfg.get("compute_type", "int8")),
            cpu_threads=int(cfg.get("cpu_threads", 2)),
            num_workers=int(cfg.get("num_workers", 1)),
        )

    def transcriber(self, *, continuous: bool = False) -> WhisperTranscriber:
        if continuous:
            if self._transcriber_continuous is None:
                self._transcriber_continuous = self._make_transcriber(continuous=True)
            return self._transcriber_continuous
        if self._transcriber_ptt is None:
            self._transcriber_ptt = self._make_transcriber(continuous=False)
        return self._transcriber_ptt

    def load_model(self, *, continuous: bool = False) -> dict[str, Any]:
        started = time.time()
        self.transcriber(continuous=continuous).load()
        kind = "segundo plano" if continuous else "push-to-talk"
        return {"ok": True, "message": f"Modelo {kind} cargado", "elapsed": round(time.time() - started, 2)}

    def unload_models(self) -> dict[str, Any]:
        if self._transcriber_ptt:
            self._transcriber_ptt.unload()
        if self._transcriber_continuous:
            self._transcriber_continuous.unload()
        self._transcriber_ptt = None
        self._transcriber_continuous = None
        gc.collect()
        return {"ok": True, "message": "Modelos liberados de memoria"}

    # ------------------------------------------------------------------ #
    # Captura + transcripción
    # ------------------------------------------------------------------ #
    def _capture(self, *, continuous: bool = False) -> AudioCaptureResult:
        cfg = self.config()
        audio = AudioInput(sample_rate=int(cfg.get("sample_rate", 16000)), channels=int(cfg.get("channels", 1)))
        max_seconds = float(cfg.get("continuous_record_seconds", cfg.get("record_seconds", 4.0)) if continuous else cfg.get("record_seconds", 4.0))
        if bool(cfg.get("smart_recording", True)):
            overrides = self._audio_profile_overrides(cfg) if continuous else {}
            return audio.record_smart_to_wav(
                max_seconds,
                stop_event=self._continuous_stop if continuous else None,
                min_seconds=float(overrides.get("min_speech", cfg.get("continuous_min_speech_seconds", cfg.get("min_record_seconds", 0.55))) if continuous else cfg.get("min_record_seconds", 0.55)),
                start_timeout=float(overrides.get("start_timeout", cfg.get("continuous_start_timeout", 1.25)) if continuous else cfg.get("start_timeout", 2.0)),
                end_silence_ms=int(overrides.get("wake_end_silence_ms", cfg.get("end_silence_ms", 650)) if continuous else cfg.get("end_silence_ms", 650)),
                energy_threshold=float(cfg.get("energy_threshold", 0.010)),
                pre_roll_ms=int(overrides.get("pre_roll_ms", 420 if continuous and str(cfg.get("audio_input_profile", "flow_gated")) != "normal" else 220)),
                keep_silence_wav=not continuous,
                short_speech_grace_ms=int(cfg.get("wake_command_bridge_ms", 0) if continuous else 0),
                short_speech_max_seconds=float(cfg.get("wake_command_bridge_short_max_seconds", 1.05)),
            )
        return audio.record_to_wav(max_seconds)

    def _capture_custom(
        self,
        *,
        max_seconds: float,
        start_timeout: float,
        min_seconds: float,
        end_silence_ms: int,
        keep_silence_wav: bool = False,
        short_speech_grace_ms: int = 0,
        short_speech_max_seconds: float = 1.05,
        pre_roll_ms: int = 220,
    ) -> AudioCaptureResult:
        """Captura parametrizada para etapas eficientes de segundo plano."""
        cfg = self.config()
        audio = AudioInput(sample_rate=int(cfg.get("sample_rate", 16000)), channels=int(cfg.get("channels", 1)))
        return audio.record_smart_to_wav(
            max_seconds,
            stop_event=self._continuous_stop,
            min_seconds=min_seconds,
            start_timeout=start_timeout,
            end_silence_ms=end_silence_ms,
            energy_threshold=float(cfg.get("energy_threshold", 0.014)),
            keep_silence_wav=keep_silence_wav,
            short_speech_grace_ms=short_speech_grace_ms,
            short_speech_max_seconds=short_speech_max_seconds,
            pre_roll_ms=int(pre_roll_ms or 220),
        )

    def _capture_wake_probe(self) -> AudioCaptureResult:
        cfg = self.config()
        overrides = self._audio_profile_overrides(cfg)
        return self._capture_custom(
            max_seconds=float(overrides.get("wake_seconds", cfg.get("wake_probe_seconds", 3.0))),
            start_timeout=float(overrides.get("start_timeout", cfg.get("wake_probe_start_timeout", cfg.get("continuous_start_timeout", 1.7)))),
            min_seconds=float(overrides.get("min_speech", cfg.get("wake_probe_min_speech_seconds", 0.42))),
            end_silence_ms=int(overrides.get("wake_end_silence_ms", cfg.get("wake_probe_end_silence_ms", 650))),
            keep_silence_wav=False,
            short_speech_grace_ms=int(overrides.get("wake_bridge_ms", cfg.get("wake_command_bridge_ms", 1350))),
            short_speech_max_seconds=float(overrides.get("wake_bridge_short_max", cfg.get("wake_command_bridge_short_max_seconds", 1.05))),
            pre_roll_ms=int(overrides.get("pre_roll_ms", 850)),
        )

    def _capture_command_after_wake(self) -> AudioCaptureResult:
        cfg = self.config()
        overrides = self._audio_profile_overrides(cfg)
        return self._capture_custom(
            max_seconds=float(overrides.get("cmd_seconds", cfg.get("command_after_wake_seconds", 3.2))),
            start_timeout=float(overrides.get("start_timeout", cfg.get("command_after_wake_start_timeout", 1.25))),
            min_seconds=float(overrides.get("min_speech", cfg.get("command_after_wake_min_speech_seconds", 0.42))),
            end_silence_ms=int(overrides.get("cmd_end_silence_ms", cfg.get("command_after_wake_end_silence_ms", 650))),
            keep_silence_wav=False,
            short_speech_grace_ms=int(cfg.get("command_pause_bridge_ms", 900)),
            short_speech_max_seconds=float(cfg.get("command_pause_bridge_short_max_seconds", 0.85)),
            pre_roll_ms=int(overrides.get("pre_roll_ms", 720)),
        )

    def _language_for_capture(self, *, continuous: bool = False) -> str | None:
        cfg = self.config()
        mode = str(cfg.get("language_mode", "es_mixed") or "es_mixed")
        # Clips de segundo plano son cortos: autodetección tiende a inventar idiomas.
        # Por eso fondo fuerza español, pero el parser acepta comandos mezclados ES/EN.
        if continuous:
            return "es"
        if mode == "auto_ptt":
            return None
        return str(cfg.get("language", "es") or "es")

    def _transcribe_capture(self, capture: AudioCaptureResult, *, continuous: bool = False) -> str:
        cfg = self.config()
        if not capture.wav_path:
            return ""
        transcription = self.transcriber(continuous=continuous).transcribe(
            capture.wav_path,
            language=self._language_for_capture(continuous=continuous),
            vad_filter=bool(cfg.get("continuous_vad_filter", False) if continuous else cfg.get("vad_filter", True)),
            beam_size=int(cfg.get("continuous_beam_size", cfg.get("beam_size", 1)) if continuous else cfg.get("beam_size", 1)),
            initial_prompt=str(cfg.get("initial_prompt", "") or ""),
            keep_file=bool(continuous and self._speaker_policy() != "open"),
        )
        return transcription.text

    def listen_once(self) -> dict[str, Any]:
        cfg = self.config()
        status = self.dependency_status()
        if not status.get("ok"):
            return {"ok": False, "stage": "deps", "message": f"Dependencias faltantes: {status}"}
        started = time.time()
        capture = self._capture(continuous=False)
        if bool(cfg.get("smart_recording", True)) and not capture.speech_started:
            return {
                "ok": False,
                "stage": "capture",
                "message": "No detecté voz",
                "transcript": "",
                "capture_seconds": round(capture.seconds, 2),
                "speech_started": False,
                "auto_stopped": bool(getattr(capture, "auto_stopped", False)),
                "rms_peak": round(float(getattr(capture, "rms_peak", 0.0)), 4),
                "elapsed": round(time.time() - started, 2),
            }
        text = self._transcribe_capture(capture, continuous=False)
        result = self.execute_text(text, source="voice")
        result.update({
            "transcript": text,
            "capture_seconds": round(capture.seconds, 2),
            "speech_started": bool(getattr(capture, "speech_started", True)),
            "auto_stopped": bool(getattr(capture, "auto_stopped", False)),
            "rms_peak": round(float(getattr(capture, "rms_peak", 0.0)), 4),
            "elapsed": round(time.time() - started, 2),
        })
        return result

    # ------------------------------------------------------------------ #
    # Escucha continua
    # ------------------------------------------------------------------ #
    def is_continuous_running(self) -> bool:
        return bool(self._continuous_thread and self._continuous_thread.is_alive())

    def start_continuous(self, callback: VoiceEventCallback | None = None) -> dict[str, Any]:
        if self.is_continuous_running():
            return {"ok": True, "message": "Escucha continua ya estaba activa"}
        status = self.dependency_status()
        if not status.get("ok"):
            return {"ok": False, "message": f"Dependencias faltantes: {status}"}
        self._continuous_callback = callback
        self._continuous_stop.clear()
        self._continuous_thread = threading.Thread(target=self._continuous_loop, daemon=True, name="WizZVoiceContinuous")
        self._continuous_thread.start()
        return {"ok": True, "message": "Escucha continua activada"}

    def stop_continuous(self) -> dict[str, Any]:
        self._continuous_stop.set()
        if bool(self.config().get("unload_model_when_continuous_stops", False)):
            if self._transcriber_continuous:
                self._transcriber_continuous.unload()
            self._transcriber_continuous = None
            gc.collect()
        return {"ok": True, "message": "Escucha continua detenida"}

    def _emit(self, payload: dict[str, Any]) -> None:
        cb = self._continuous_callback
        if cb:
            try:
                cb(payload)
            except Exception:
                _LOG.debug("[Voice] callback continuo falló", exc_info=True)

    def _should_emit_idle(self) -> bool:
        now = time.time()
        if now - self._last_idle_emit >= 12.0:
            self._last_idle_emit = now
            return True
        return False

    def _non_wake_pause_seconds(self) -> float:
        cfg = self.config()
        base_ms = int(cfg.get("continuous_pause_after_non_wake_ms", 550))
        if bool(cfg.get("adaptive_non_wake_backoff", False)):
            step_ms = int(cfg.get("non_wake_backoff_step_ms", 250))
            max_ms = int(cfg.get("non_wake_backoff_max_ms", 1800))
            base_ms = min(max_ms, base_ms + max(0, self._non_wake_streak - 1) * step_ms)
        return max(0.12, min(0.90, base_ms / 1000.0))

    def _register_non_wake(self) -> None:
        self._non_wake_streak = min(8, self._non_wake_streak + 1)

    def _reset_non_wake(self) -> None:
        self._non_wake_streak = 0

    def _wake_policy_preview(self, text: str) -> tuple[bool, str, str | None]:
        """Chequeo barato después de transcribir, antes de ejecutar.

        No evita el costo mínimo de ASR, porque para saber si dijo "wizz"
        necesitamos texto. Pero evita que cualquier conversación pase al parser,
        reduce callbacks/UI y mete una pausa larga para no transcribir cada frase
        seguida mientras juegas o hablas por Discord.
        """
        return self._apply_wake_word_policy(text, "continuous")

    def _continuous_loop(self) -> None:
        self._emit({"event": "continuous_started", "ok": True, "message": "Escucha continua activa"})
        while not self._continuous_stop.is_set():
            cfg = self.config()
            started = time.time()
            try:
                strategy = str(cfg.get("continuous_strategy", "wake_then_command"))
                if strategy == "wake_then_command" and bool(cfg.get("continuous_require_wake_word", True)):
                    self._continuous_loop_wake_then_command(cfg, started)
                else:
                    self._continuous_loop_full_phrase(cfg, started)
            except Exception as exc:
                _LOG.exception("[Voice] Error en escucha continua")
                self._emit({"event": "error", "ok": False, "message": f"Error en escucha continua: {exc}", "transcript": ""})
                time.sleep(max(0.25, int(self.config().get("continuous_error_sleep_ms", 1400)) / 1000.0))
        self._emit({"event": "continuous_stopped", "ok": True, "message": "Escucha continua detenida"})

    def _continuous_loop_wake_then_command(self, cfg: dict[str, Any], started: float) -> None:
        """Modo equilibrado: primero intenta capturar frase completa.

        Fase 27 mantiene frase completa y tolera una pausa corta después del
        activador. Ejemplo: "pc" + 1 segundo + "apaga la luz" debería quedar
        en la misma captura antes de transcribir. Solo usa segunda captura si
        realmente quedó únicamente el activador.
        """
        capture = self._capture_wake_probe()
        if self._continuous_stop.is_set():
            return
        if not capture.speech_started:
            if self._should_emit_idle():
                self._emit({
                    "event": "idle",
                    "ok": False,
                    "message": "Silencio",
                    "transcript": "",
                    "capture_seconds": round(capture.seconds, 2),
                    "rms_peak": round(float(capture.rms_peak), 4),
                })
            time.sleep(max(0.05, int(cfg.get("continuous_idle_sleep_ms", 420)) / 1000.0))
            return

        min_peak = float(cfg.get("wake_probe_min_rms_peak", cfg.get("continuous_min_rms_peak", 0.010)))
        if float(capture.rms_peak) < min_peak:
            if self._should_emit_idle():
                self._emit({
                    "event": "idle",
                    "ok": False,
                    "message": "Ruido bajo ignorado",
                    "transcript": "",
                    "capture_seconds": round(capture.seconds, 2),
                    "rms_peak": round(float(capture.rms_peak), 4),
                })
            time.sleep(max(0.05, int(cfg.get("continuous_idle_sleep_ms", 420)) / 1000.0))
            return

        # Fase 26: no convertir cualquier pulso corto en wake word.
        # Eso generaba falsos positivos con Voicemeeter/ruido y mandaba a Whisper
        # una segunda captura innecesaria. Se prefiere activador + comando completo.
        min_transcribe = float(cfg.get("wake_min_transcribe_seconds", 0.72))
        short_candidate = (
            bool(cfg.get("wake_short_candidate_enabled", False))
            and float(capture.seconds) >= float(cfg.get("wake_short_candidate_min_seconds", 0.35))
            and float(capture.seconds) <= float(cfg.get("wake_short_candidate_max_seconds", 0.55))
            and float(capture.rms_peak) >= float(cfg.get("wake_short_candidate_min_rms_peak", max(0.060, min_peak)))
        )
        if float(capture.seconds) < min_transcribe:
            if short_candidate:
                self._handle_candidate_wake_without_asr(cfg, started, capture, reason="Clip corto tratado como posible palabra clave")
            else:
                if self._should_emit_idle():
                    self._emit({
                        "event": "wake_ignored",
                        "ok": False,
                        "message": "Clip demasiado corto; ignorado",
                        "transcript": "",
                        "capture_seconds": round(capture.seconds, 2),
                        "rms_peak": round(float(capture.rms_peak), 4),
                        "elapsed": round(time.time() - started, 2),
                        "profile": cfg.get("performance_profile", "balanced"),
                    })
                time.sleep(0.12)
            return

        self._emit({"event": "transcribing", "ok": True, "message": "Verificando palabra clave…"})
        wake_text = self._transcribe_capture(capture, continuous=True)

        if self._looks_like_hallucination(wake_text, capture_seconds=float(capture.seconds)):
            # Fase 26: una alucinación NUNCA debe promoverse a wake.
            # Antes esto podía activar "[posible palabra clave]" y generar comandos falsos.
            self._register_non_wake()
            self._emit({
                "event": "wake_ignored",
                "ok": False,
                "message": "Ruido/ASR repetitivo descartado; no se activó wake",
                "transcript": "[ruido repetitivo descartado]" if bool(cfg.get("continuous_hide_hallucinated_text", True)) else wake_text,
                "capture_seconds": round(capture.seconds, 2),
                "rms_peak": round(float(capture.rms_peak), 4),
                "elapsed": round(time.time() - started, 2),
                "profile": cfg.get("performance_profile", "balanced"),
            })
            time.sleep(max(0.08, int(cfg.get("continuous_hallucination_pause_ms", 140)) / 1000.0))
            return

        wake_ok, command_text, wake_error = self._detect_wake_prefix(wake_text)
        if not wake_ok:
            self._register_non_wake()
            if self._should_emit_idle():
                safe_wake_text = wake_text
                if bool(cfg.get("continuous_hide_hallucinated_text", True)) and (len(wake_text) > 180 or self._looks_like_hallucination(wake_text, capture_seconds=float(capture.seconds))):
                    safe_wake_text = "[ruido/texto no-wake descartado]"
                self._emit({
                    "event": "wake_ignored",
                    "ok": False,
                    "message": wake_error or "Ignorado: debe empezar con palabra clave",
                    "transcript": safe_wake_text,
                    "capture_seconds": round(capture.seconds, 2),
                    "rms_peak": round(float(capture.rms_peak), 4),
                    "elapsed": round(time.time() - started, 2),
                    "profile": cfg.get("performance_profile", "balanced"),
                    "backoff": round(self._non_wake_pause_seconds(), 2),
                })
            time.sleep(self._non_wake_pause_seconds())
            return

        self._reset_non_wake()
        capture_seconds = round(capture.seconds, 2)
        rms_peak = round(float(capture.rms_peak), 4)

        # Si el primer clip ya contiene comando útil, ejecuta directo.
        # Si quedó incompleto o fue solo el activador, toma una segunda captura
        # y CONCATENA lo escuchado. Esto evita que el log pierda "pc/wizz" y
        # reduce cortes como "apaga la".
        first_command_text = command_text or ""
        test_intent = self.parser.parse(first_command_text) if first_command_text else None
        used_followup = False
        if not first_command_text or not (test_intent and test_intent.ok):
            self._emit({
                "event": "wake_detected",
                "ok": True,
                "message": "Activador detectado. Completa el comando…" if not first_command_text else "Comando parcial. Escuchando continuación…",
                "transcript": wake_text,
            })
            cmd_capture = self._capture_command_after_wake()
            if self._continuous_stop.is_set():
                return
            if not cmd_capture.speech_started:
                self._emit({
                    "event": "wake_ignored",
                    "ok": False,
                    "message": "Escuché el activador, pero no escuché comando después",
                    "transcript": wake_text,
                    "capture_seconds": round(capture.seconds + cmd_capture.seconds, 2),
                    "elapsed": round(time.time() - started, 2),
                    "profile": cfg.get("performance_profile", "balanced"),
                })
                time.sleep(0.14)
                return
            followup_text = self._transcribe_capture(cmd_capture, continuous=True)
            if self._looks_like_hallucination(followup_text, capture_seconds=float(cmd_capture.seconds)):
                self._emit({
                    "event": "wake_ignored",
                    "ok": False,
                    "message": "Comando descartado por repetición/ruido",
                    "transcript": followup_text,
                    "wake_transcript": wake_text,
                    "capture_seconds": round(capture.seconds + cmd_capture.seconds, 2),
                    "elapsed": round(time.time() - started, 2),
                    "profile": cfg.get("performance_profile", "balanced"),
                })
                time.sleep(0.14)
                return
            command_text = (first_command_text + " " + followup_text).strip()
            used_followup = True
            capture_seconds = round(capture.seconds + cmd_capture.seconds, 2)
            rms_peak = round(max(float(capture.rms_peak), float(cmd_capture.rms_peak)), 4)

        display_transcript = wake_text if not used_followup else (wake_text + " + " + command_text).strip()
        verify_capture = cmd_capture if used_followup and 'cmd_capture' in locals() else capture
        speaker_check = self._verify_speaker_capture(verify_capture)
        if not speaker_check.get("ok"):
            self._emit({
                "event": "wake_ignored",
                "ok": False,
                "message": speaker_check.get("message", "Voz no verificada"),
                "transcript": display_transcript,
                "command_transcript": command_text,
                "wake_transcript": wake_text,
                "speaker_similarity": speaker_check.get("similarity"),
                "speaker_mode": speaker_check.get("mode"),
                "capture_seconds": capture_seconds,
                "rms_peak": rms_peak,
                "elapsed": round(time.time() - started, 2),
                "profile": cfg.get("performance_profile", "balanced"),
            })
            time.sleep(0.16)
            return
        result = self.execute_text(command_text, source="continuous_command")
        result.update({
            "speaker_similarity": speaker_check.get("similarity"),
            "speaker_mode": speaker_check.get("mode"),
            "event": "command" if result.get("ok") else "wake_ignored",
            "transcript": display_transcript,
            "command_transcript": command_text,
            "wake_transcript": wake_text,
            "capture_seconds": capture_seconds,
            "speech_started": True,
            "auto_stopped": bool(capture.auto_stopped),
            "rms_peak": rms_peak,
            "elapsed": round(time.time() - started, 2),
            "profile": cfg.get("performance_profile", "balanced"),
        })
        self._emit(result)
        time.sleep(max(0.12, int(cfg.get("continuous_pause_after_command_ms", 220)) / 1000.0 if result.get("ok") else 0.16))

    def _handle_candidate_wake_without_asr(self, cfg: dict[str, Any], started: float, capture: AudioCaptureResult, *, reason: str) -> None:
        """Fallback para activadores cortos como "wiz"/"pc".

        Whisper suele alucinar con clips de menos de 0.8s. Para no perder el
        comando, si el pulso fue claro lo tratamos como posible wake y escuchamos
        el comando inmediatamente. Solo ejecuta si el parser entiende una acción.
        """
        self._emit({
            "event": "wake_detected",
            "ok": True,
            "message": f"{reason}. Escuchando comando…",
            "transcript": "[posible palabra clave]",
            "capture_seconds": round(capture.seconds, 2),
            "rms_peak": round(float(capture.rms_peak), 4),
        })
        cmd_capture = self._capture_command_after_wake()
        if self._continuous_stop.is_set():
            return
        if not cmd_capture.speech_started:
            self._emit({
                "event": "wake_ignored",
                "ok": False,
                "message": "Posible palabra clave, pero no escuché comando después",
                "transcript": "",
                "capture_seconds": round(capture.seconds + cmd_capture.seconds, 2),
                "elapsed": round(time.time() - started, 2),
                "profile": cfg.get("performance_profile", "balanced"),
            })
            time.sleep(0.16)
            return
        command_text = self._transcribe_capture(cmd_capture, continuous=True)
        if self._looks_like_hallucination(command_text, capture_seconds=float(cmd_capture.seconds)):
            self._emit({
                "event": "wake_ignored",
                "ok": False,
                "message": "Comando descartado por repetición/ruido",
                "transcript": "[ruido descartado]",
                "capture_seconds": round(capture.seconds + cmd_capture.seconds, 2),
                "elapsed": round(time.time() - started, 2),
                "profile": cfg.get("performance_profile", "balanced"),
            })
            time.sleep(0.14)
            return
        speaker_check = self._verify_speaker_capture(cmd_capture)
        if not speaker_check.get("ok"):
            self._emit({
                "event": "wake_ignored",
                "ok": False,
                "message": speaker_check.get("message", "Voz no verificada"),
                "transcript": f"[activador corto] {command_text}".strip(),
                "command_transcript": command_text,
                "speaker_similarity": speaker_check.get("similarity"),
                "speaker_mode": speaker_check.get("mode"),
                "capture_seconds": round(capture.seconds + cmd_capture.seconds, 2),
                "rms_peak": round(max(float(capture.rms_peak), float(cmd_capture.rms_peak)), 4),
                "elapsed": round(time.time() - started, 2),
                "profile": cfg.get("performance_profile", "balanced"),
            })
            time.sleep(0.16)
            return
        # Ejecutar solo si el parser entiende una acción. Así un ruido corto no
        # convierte una conversación normal en comando.
        result = self.execute_text(command_text, source="continuous_candidate")
        if not result.get("ok"):
            result["message"] = result.get("message") or "Posible palabra clave, pero comando no reconocido"
        display_transcript = f"[activador corto] {command_text}".strip()
        result.update({
            "event": "command" if result.get("ok") else "wake_ignored",
            "transcript": display_transcript,
            "command_transcript": command_text,
            "wake_transcript": "[activador corto]",
            "capture_seconds": round(capture.seconds + cmd_capture.seconds, 2),
            "speech_started": True,
            "auto_stopped": bool(cmd_capture.auto_stopped),
            "rms_peak": round(max(float(capture.rms_peak), float(cmd_capture.rms_peak)), 4),
            "elapsed": round(time.time() - started, 2),
            "profile": cfg.get("performance_profile", "balanced"),
        })
        self._emit(result)
        time.sleep(max(0.12, int(cfg.get("continuous_pause_after_command_ms", 220)) / 1000.0) if result.get("ok") else 0.16)

    def _continuous_loop_full_phrase(self, cfg: dict[str, Any], started: float) -> None:
        """Modo legacy: captura frase completa y luego verifica wake word."""
        capture = self._capture(continuous=True)
        if self._continuous_stop.is_set():
            return
        if not capture.speech_started:
            if self._should_emit_idle():
                self._emit({
                    "event": "idle",
                    "ok": False,
                    "message": "Silencio",
                    "transcript": "",
                    "capture_seconds": round(capture.seconds, 2),
                    "rms_peak": round(float(capture.rms_peak), 4),
                })
            time.sleep(max(0.05, int(cfg.get("continuous_idle_sleep_ms", 900)) / 1000.0))
            return

        min_speech = float(cfg.get("continuous_min_speech_seconds", 0.85))
        min_peak = float(cfg.get("continuous_min_rms_peak", 0.016))
        if capture.seconds < min_speech or float(capture.rms_peak) < min_peak:
            if self._should_emit_idle():
                self._emit({
                    "event": "idle",
                    "ok": False,
                    "message": "Ruido corto ignorado",
                    "transcript": "",
                    "capture_seconds": round(capture.seconds, 2),
                    "rms_peak": round(float(capture.rms_peak), 4),
                })
            time.sleep(max(0.05, int(cfg.get("continuous_idle_sleep_ms", 900)) / 1000.0))
            return

        self._emit({"event": "transcribing", "ok": True, "message": "Verificando palabra clave…"})
        text = self._transcribe_capture(capture, continuous=True)
        allowed, _, wake_error = self._wake_policy_preview(text)
        if not allowed:
            self._register_non_wake()
            if self._should_emit_idle():
                self._emit({
                    "event": "wake_ignored",
                    "ok": False,
                    "message": wake_error or "Ignorado: falta palabra clave al inicio",
                    "transcript": text,
                    "capture_seconds": round(capture.seconds, 2),
                    "rms_peak": round(float(capture.rms_peak), 4),
                    "elapsed": round(time.time() - started, 2),
                    "profile": cfg.get("performance_profile", "eco"),
                    "backoff": round(self._non_wake_pause_seconds(), 2),
                })
            time.sleep(self._non_wake_pause_seconds())
            return

        self._reset_non_wake()
        speaker_check = self._verify_speaker_capture(capture)
        if not speaker_check.get("ok"):
            self._emit({
                "event": "wake_ignored",
                "ok": False,
                "message": speaker_check.get("message", "Voz no verificada"),
                "transcript": text,
                "speaker_similarity": speaker_check.get("similarity"),
                "speaker_mode": speaker_check.get("mode"),
                "capture_seconds": round(capture.seconds, 2),
                "rms_peak": round(float(capture.rms_peak), 4),
                "elapsed": round(time.time() - started, 2),
                "profile": cfg.get("performance_profile", "eco"),
            })
            time.sleep(0.16)
            return
        result = self.execute_text(text, source="continuous")
        result.update({
            "speaker_similarity": speaker_check.get("similarity"),
            "speaker_mode": speaker_check.get("mode"),
            "event": "command",
            "transcript": text,
            "capture_seconds": round(capture.seconds, 2),
            "speech_started": True,
            "auto_stopped": bool(capture.auto_stopped),
            "rms_peak": round(float(capture.rms_peak), 4),
            "elapsed": round(time.time() - started, 2),
            "profile": cfg.get("performance_profile", "eco"),
        })
        self._emit(result)
        time.sleep(max(0.12, int(cfg.get("continuous_pause_after_command_ms", 220)) / 1000.0))

    # ------------------------------------------------------------------ #
    # Parser + ejecución
    # ------------------------------------------------------------------ #
    def _wake_aliases(self) -> list[str]:
        """Alias configurables para activación.

        Importante: en fase 20 ya no forzamos solo wizz/wiz. Si el usuario
        quiere decir "pc" o "pese", se permite, pero sigue exigiéndose prefijo.
        """
        cfg = self.config()
        words = cfg.get("wake_words", ["wizz", "wiz"])
        if isinstance(words, str):
            words = [w.strip() for w in words.split(",") if w.strip()]

        alias_map = {
            "wizz": ["wizz", "wiz", "wis", "whiz", "weez", "wisa", "muisa", "musa", "miza", "guis", "guiz"],
            "wiz": ["wiz", "wizz", "wis", "whiz", "weez", "wisa", "muisa", "musa", "miza", "guis", "guiz"],
            # PC dicho en español suele caer como "pese", "pe ce", "pecé" o variantes.
            "pc": ["pc", "p c", "pe ce", "pece", "pese", "pes e", "pesee", "pesi", "pisi", "pisí", "piece", "pee see"],
            "pese": ["pese", "pc", "p c", "pe ce", "pece", "pes e", "pesee", "pesi", "pisi", "pisí", "piece", "pee see"],
        }
        out: list[str] = []
        for raw in words:
            base = normalize_text(str(raw))
            if not base:
                continue
            candidates = alias_map.get(base, [base])
            # Alias automático para frases con espacios: "ok luz" etc.
            if " " in base and base not in candidates:
                candidates.append(base)
            for item in candidates:
                item = normalize_text(item)
                if item and item not in out:
                    out.append(item)
        return sorted(out or ["wizz", "wiz"], key=len, reverse=True)

    def _detect_wake_prefix(self, text: str) -> tuple[bool, str, str | None]:
        norm = normalize_text(text)
        if not norm:
            return False, "", "Ignorado: no se entendió audio"
        aliases = self._wake_aliases()
        for word in aliases:
            if norm == word:
                return True, "", None
            if norm.startswith(word + " "):
                return True, norm[len(word):].strip(), None
        allowed = ", ".join(self.config().get("wake_words", ["wizz", "wiz"]))
        return False, norm, f"Ignorado: debe empezar con palabra clave ({allowed})"

    def _looks_like_hallucination(self, text: str, *, capture_seconds: float = 0.0) -> bool:
        """Filtra alucinaciones típicas de Whisper en clips cortos/ruido.

        Ejemplo real reportado: "el truco, con el truco..." repetido muchas veces.
        """
        raw = (text or "").strip()
        norm = normalize_text(raw)
        if not norm:
            return False
        words = norm.split()
        if len(raw) > 140 and capture_seconds and capture_seconds < 1.2:
            return True
        if len(words) >= 10:
            # Repetición fuerte de una palabra o bigrama/trigrama.
            from collections import Counter
            word_counts = Counter(words)
            if word_counts.most_common(1)[0][1] / max(1, len(words)) >= 0.38:
                return True
            for n in (2, 3, 4):
                grams = [tuple(words[i:i+n]) for i in range(0, len(words) - n + 1)]
                if grams:
                    top = Counter(grams).most_common(1)[0][1]
                    if top >= 4 and top / max(1, len(grams)) >= 0.28:
                        return True
        # Frases basura muy comunes en modelos Whisper con ruido/clip corto.
        bad_patterns = (
            "con el truco", "el truco", "gracias por ver", "suscribete", "subtitulos", "transcripcion",
        )
        return any(p in norm for p in bad_patterns) and not any(w in norm.split()[:3] for w in self._wake_aliases())

    def _apply_wake_word_policy(self, text: str, source: str) -> tuple[bool, str, str | None]:
        cfg = self.config()
        # Push-to-talk/manual no exigen wake word. Segundo plano sí, siempre.
        if source != "continuous" or not bool(cfg.get("continuous_require_wake_word", True)):
            return True, text, None

        if self._looks_like_hallucination(text, capture_seconds=0.0):
            return False, text, "Ignorado: transcripción repetida/ruido"

        found, remainder, error = self._detect_wake_prefix(text)
        if not found:
            return False, text, error
        if bool(cfg.get("continuous_require_command_after_wake", True)) and not remainder:
            return False, text, "Ignorado: escuché WizZ, pero no un comando"
        return True, remainder or text, None

    def execute_text(self, text: str, source: str = "manual") -> dict[str, Any]:
        allowed, parsed_text, wake_error = self._apply_wake_word_policy(text, source)
        if not allowed:
            return {
                "ok": False,
                "source": source,
                "transcript": text,
                "confidence": 0.0,
                "message": wake_error or "Ignorado",
                "action": None,
                "intent_source": "wake_word",
            }

        intent = self.parser.parse(parsed_text)
        if not intent.ok or not intent.action:
            return {
                "ok": False,
                "source": source,
                "transcript": text,
                "confidence": intent.confidence,
                "message": intent.reason,
                "action": None,
            }
        cfg = self.config()
        cooldown = max(0, int(cfg.get("cooldown_ms", 850) or 850)) / 1000.0
        now = time.time()
        if source in ("voice", "continuous", "continuous_command", "continuous_candidate") and now - self._last_exec_at < cooldown:
            return {
                "ok": False,
                "source": source,
                "transcript": text,
                "confidence": intent.confidence,
                "message": "Ignorado por cooldown",
                "action": intent.action,
            }
        try:
            label = self.registry.execute(intent.action)
            self._last_exec_at = now
            if intent.training_id:
                self.training_manager.mark_used(intent.training_id)
            return {
                "ok": True,
                "source": source,
                "transcript": text,
                "confidence": intent.confidence,
                "message": f"Ejecutado: {label}",
                "action": intent.action,
                "intent_source": intent.source,
            }
        except Exception as exc:
            _LOG.exception("[Voice] Error ejecutando acción")
            return {
                "ok": False,
                "source": source,
                "transcript": text,
                "confidence": intent.confidence,
                "message": f"Error ejecutando: {exc}",
                "action": intent.action,
            }

    def available_actions(self) -> list[dict[str, Any]]:
        return self.registry.build_actions()

    def action_by_id(self, action_id: str) -> dict[str, Any] | None:
        return self.registry.get_action(action_id)

    def train_phrase(self, phrase: str, action_id: str) -> dict[str, Any]:
        action = self.action_by_id(action_id)
        if not action:
            raise ValueError("Acción no encontrada")
        stable = {k: action.get(k) for k in ("id", "category", "name", "type", "method", "value") if k in action}
        item = self.training_manager.add_entry(phrase, stable)
        self.parser = VoiceIntentParser(self.wiz)
        return item
