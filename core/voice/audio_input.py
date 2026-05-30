from __future__ import annotations

import queue
import tempfile
import threading
import time
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AudioCaptureResult:
    wav_path: str
    seconds: float
    sample_rate: int
    speech_started: bool = True
    rms_peak: float = 0.0
    auto_stopped: bool = False


def _require_audio_deps():
    try:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore
        return np, sd
    except Exception as exc:  # pragma: no cover - depende del entorno del usuario
        raise RuntimeError(
            "Faltan dependencias de audio. Ejecuta: python -m pip install sounddevice numpy"
        ) from exc


class AudioInput:
    """Grabación para voz.

    Fase 12 agrega corte automático por silencio para que push-to-talk no espere
    siempre los 4/6/8 segundos completos. Es un VAD simple por RMS, sin meter
    dependencias pesadas.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = int(sample_rate or 16000)
        self.channels = int(channels or 1)

    def record_to_wav(self, seconds: float = 4.0) -> AudioCaptureResult:
        """Grabación fija legacy. Se mantiene como fallback estable."""
        np, sd = _require_audio_deps()
        seconds = max(1.0, min(12.0, float(seconds or 4.0)))
        frames = int(self.sample_rate * seconds)
        audio = sd.rec(frames, samplerate=self.sample_rate, channels=self.channels, dtype="float32")
        sd.wait()
        audio = np.asarray(audio).reshape(-1)
        return self._write_float_wav(audio, seconds=seconds, rms_peak=float(np.max(np.abs(audio))) if audio.size else 0.0)

    def record_smart_to_wav(
        self,
        max_seconds: float = 4.0,
        *,
        stop_event: threading.Event | None = None,
        min_seconds: float = 0.55,
        start_timeout: float = 2.0,
        end_silence_ms: int = 650,
        energy_threshold: float = 0.010,
        pre_roll_ms: int = 220,
        block_ms: int = 40,
        keep_silence_wav: bool = True,
        short_speech_grace_ms: int = 0,
        short_speech_max_seconds: float = 1.05,
        input_gain: float = 1.0,
        normalize_target_rms: float = 0.0,
        normalize_max_gain: float = 1.0,
    ) -> AudioCaptureResult:
        """Graba hasta detectar fin de habla.

        - max_seconds: límite duro de seguridad.
        - start_timeout: si no detecta voz, corta antes.
        - end_silence_ms: silencio requerido después de hablar para cortar.
        - energy_threshold: sensibilidad. Más bajo = más sensible.
        """
        np, sd = _require_audio_deps()

        max_seconds = max(1.0, min(12.0, float(max_seconds or 4.0)))
        min_seconds = max(0.25, min(max_seconds, float(min_seconds or 0.55)))
        start_timeout = max(0.5, min(max_seconds, float(start_timeout or 2.0)))
        end_silence_s = max(0.25, min(2.5, int(end_silence_ms or 650) / 1000.0))
        short_speech_grace_s = max(0.0, min(2.8, int(short_speech_grace_ms or 0) / 1000.0))
        short_speech_max_s = max(0.30, min(2.5, float(short_speech_max_seconds or 1.05)))
        # Phase 42: VAD adaptativo cerca/lejos.
        # Antes el umbral mínimo seguía siendo algo alto cuando te alejabas.
        # Bajamos el piso permitido y la protección real queda en activador+ASR,
        # no en exigir que la voz sea fuerte.
        threshold_floor = max(0.0018, min(0.08, float(energy_threshold or 0.010)))
        blocksize = max(160, int(self.sample_rate * max(20, min(100, int(block_ms or 40))) / 1000))
        pre_roll_blocks = max(1, int(max(0, int(pre_roll_ms or 220)) / max(1, int(block_ms or 40))))

        # Phase 43: cola acotada. En reposo no necesitamos acumular audio antiguo;
        # si el callback se adelanta, descartamos el bloque más viejo. Esto baja
        # trabajo pendiente y evita latencia/costo extra sin tocar precisión real.
        q: queue.Queue = queue.Queue(maxsize=24)

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                # No levantamos error por overflow menor; guardamos igual.
                pass
            try:
                q.put_nowait(indata.copy())
            except queue.Full:
                try:
                    q.get_nowait()
                except Exception:
                    pass
                try:
                    q.put_nowait(indata.copy())
                except Exception:
                    pass

        started_at = time.monotonic()
        speech_started = False
        first_speech_at: float | None = None
        last_speech_at: float | None = None
        auto_stopped = False
        rms_peak = 0.0
        chunks: list = []
        prebuffer: deque = deque(maxlen=pre_roll_blocks)
        noise_values: list[float] = []

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=blocksize,
            callback=callback,
        ):
            while True:
                if stop_event is not None and stop_event.is_set():
                    auto_stopped = True
                    break
                now = time.monotonic()
                elapsed = now - started_at
                if elapsed >= max_seconds:
                    break
                try:
                    # Phase 43: timeout proporcional al bloque de audio. Con bloques
                    # de 80ms no hace falta despertar el loop con tanta frecuencia.
                    block = q.get(timeout=max(0.06, min(0.18, (blocksize / max(1, self.sample_rate)) * 1.5)))
                except queue.Empty:
                    continue

                block = np.asarray(block, dtype=np.float32).reshape(-1)
                if block.size == 0:
                    continue
                rms = float(np.sqrt(np.mean(np.square(block))))
                rms_peak = max(rms_peak, float(np.max(np.abs(block))))

                # Calibración liviana del ruido ambiente.
                #
                # Fase 29: antes se agregaban TODOS los bloques de los primeros
                # 450 ms a noise_values. Si el usuario empezaba hablando de
                # inmediato ("pc apaga la luz" de corrido), esos primeros bloques
                # eran VOZ, la mediana subía demasiado y el VAD dejaba de ver el
                # inicio como habla. Resultado: había que hablar muy marcado.
                #
                # Ahora solo usamos bloques claramente bajos para calibrar ruido.
                # La voz de arranque no envenena el umbral.
                if not speech_started and elapsed < 0.45:
                    if rms <= threshold_floor * 2.8:
                        noise_values.append(rms)
                if noise_values:
                    dynamic_noise = float(np.percentile(noise_values, 70)) * 2.6
                else:
                    dynamic_noise = 0.0
                threshold = max(threshold_floor, dynamic_noise)
                # No permitas que la calibración dinámica suba tanto que se coma
                # sílabas iniciales como "pc", "pese" o "wiz".
                threshold = min(threshold, max(threshold_floor, threshold_floor * 3.0))

                is_speech = rms >= threshold
                if not speech_started:
                    prebuffer.append(block)
                    if is_speech:
                        speech_started = True
                        first_speech_at = now
                        last_speech_at = now
                        chunks.extend(list(prebuffer))
                        prebuffer.clear()
                    elif elapsed >= start_timeout:
                        # No escuchó voz: guarda lo poco capturado para que Whisper
                        # pueda devolver vacío, pero no espera todo el máximo.
                        chunks.extend(list(prebuffer))
                        auto_stopped = True
                        break
                    continue

                chunks.append(block)
                if is_speech:
                    if first_speech_at is None:
                        first_speech_at = now
                    last_speech_at = now
                elif last_speech_at is not None:
                    captured_elapsed = now - started_at
                    speech_span = max(0.0, last_speech_at - (first_speech_at or last_speech_at))
                    required_silence = end_silence_s
                    # Micrófonos con gate/Voicemeeter pueden cortar a cero justo
                    # después de decir el activador: "pc ... apaga la luz".
                    # Si lo escuchado hasta ahora fue muy corto, esperamos un
                    # poco más antes de cerrar para capturar la pausa natural.
                    if short_speech_grace_s > 0 and speech_span <= short_speech_max_s:
                        required_silence = max(required_silence, short_speech_grace_s)
                    if captured_elapsed >= min_seconds and now - last_speech_at >= required_silence:
                        auto_stopped = True
                        break

        if not speech_started and not keep_silence_wav:
            # Optimización importante para segundo plano: si no hubo voz real,
            # no escribimos WAV temporal cada 1-2 segundos. Menos disco, menos CPU,
            # menos trabajo para el recolector y menos impacto al jugar.
            elapsed = min(max_seconds, time.monotonic() - started_at)
            return AudioCaptureResult(
                wav_path="",
                seconds=float(elapsed),
                sample_rate=self.sample_rate,
                speech_started=False,
                rms_peak=float(rms_peak),
                auto_stopped=bool(auto_stopped),
            )

        if chunks:
            audio = np.concatenate(chunks).astype(np.float32)
        else:
            audio = np.zeros(int(self.sample_rate * 0.15), dtype=np.float32)
        # Phase 40: trailing pad liviano. Con Voicemeeter/gate el último
        # fonema puede quedar demasiado pegado al fin del WAV y Whisper pierde
        # palabras finales como "luz", "cien" o "cincuenta". Un pad corto de
        # silencio no cambia el comando, no aumenta CPU de forma relevante y
        # mejora estabilidad del ASR.
        try:
            tail = np.zeros(int(self.sample_rate * 0.08), dtype=np.float32)
            audio = np.concatenate([audio, tail]).astype(np.float32)
        except Exception:
            pass
        # Phase 41: ganancia/normalización para voz lejana.
        # No cambia el VAD ni sube CPU de forma relevante; solo entrega a Whisper
        # un WAV con nivel más usable cuando hablas lejos del micrófono.
        try:
            gain = max(0.25, min(5.0, float(input_gain or 1.0)))
            if gain != 1.0:
                audio = audio * gain
            target = max(0.0, min(0.20, float(normalize_target_rms or 0.0)))
            max_gain = max(1.0, min(8.0, float(normalize_max_gain or 1.0)))
            if target > 0 and audio.size:
                rms_all = float(np.sqrt(np.mean(np.square(audio))))
                if 0.0001 < rms_all < target:
                    audio = audio * min(max_gain, target / rms_all)
            audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
        except Exception:
            pass
        # Phase 42: normalización automática para distancia variable.
        # Si estás lejos, sube nivel del WAV antes de Whisper. Si estás cerca,
        # casi no actúa. No aumenta hilos/modelo y mantiene precisión.
        try:
            gain = max(0.25, min(5.0, float(input_gain or 1.0)))
            if gain != 1.0:
                audio = audio * gain
            target = max(0.0, min(0.20, float(normalize_target_rms or 0.0)))
            max_gain = max(1.0, min(8.0, float(normalize_max_gain or 1.0)))
            if target > 0 and audio.size:
                rms_all = float(np.sqrt(np.mean(np.square(audio))))
                if 0.0001 < rms_all < target:
                    audio = audio * min(max_gain, target / rms_all)
            audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
        except Exception:
            pass
        seconds = float(len(audio)) / float(self.sample_rate)
        return self._write_float_wav(
            audio,
            seconds=seconds,
            speech_started=speech_started,
            rms_peak=rms_peak,
            auto_stopped=auto_stopped,
        )

    def _write_float_wav(
        self,
        audio,
        *,
        seconds: float,
        speech_started: bool = True,
        rms_peak: float = 0.0,
        auto_stopped: bool = False,
    ) -> AudioCaptureResult:
        np, _ = _require_audio_deps()
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        audio = np.nan_to_num(audio)
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767.0).astype(np.int16)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        path = Path(tmp.name)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm.tobytes())
        return AudioCaptureResult(
            str(path),
            seconds,
            self.sample_rate,
            speech_started=speech_started,
            rms_peak=float(rms_peak),
            auto_stopped=bool(auto_stopped),
        )
