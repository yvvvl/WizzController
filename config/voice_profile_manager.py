from __future__ import annotations

import math
import time
import wave
from pathlib import Path
from typing import Any

from .base_manager import JsonManager


class VoiceProfileManager(JsonManager):
    """Perfil vocal local y liviano.

    No es biometría fuerte ni seguridad bancaria. Es un filtro práctico para
    evitar que otras voces ejecuten comandos casualmente en la habitación.
    Solo se usa después de detectar activador/comando, así no consume recursos
    mientras hay silencio o conversación normal.
    """

    DEFAULT = {
        "enabled": False,
        "samples": [],
        "centroid": None,
        "updated_at": None,
    }

    def __init__(self) -> None:
        super().__init__("voice_profile.json", default_data=dict(self.DEFAULT))
        if not isinstance(self.data, dict):
            self.data = dict(self.DEFAULT)
            self.save()
        changed = False
        for k, v in self.DEFAULT.items():
            if k not in self.data:
                self.data[k] = v
                changed = True
        if changed:
            self.save()

    def status(self) -> dict[str, Any]:
        samples = self.data.get("samples") if isinstance(self.data, dict) else []
        return {
            "enabled": bool(self.data.get("enabled", False)),
            "sample_count": len(samples) if isinstance(samples, list) else 0,
            "trained": bool(self.data.get("centroid")),
            "updated_at": self.data.get("updated_at"),
        }

    def set_enabled(self, enabled: bool) -> None:
        self.data["enabled"] = bool(enabled)
        self.save()

    def clear(self) -> None:
        self.data = dict(self.DEFAULT)
        self.save()

    def add_sample_from_wav(self, wav_path: str) -> dict[str, Any]:
        features = self.extract_features_from_wav(wav_path)
        if not features:
            raise RuntimeError("No se pudo extraer huella vocal del audio")
        samples = self.data.get("samples")
        if not isinstance(samples, list):
            samples = []
        samples.append(features)
        # Mantiene pocas muestras para que el JSON no crezca ni se vuelva lento.
        samples = samples[-12:]
        self.data["samples"] = samples
        self.data["centroid"] = self._mean_vector(samples)
        self.data["enabled"] = True
        self.data["updated_at"] = int(time.time())
        self.save()
        return self.status()

    def similarity_to_wav(self, wav_path: str) -> float | None:
        centroid = self.data.get("centroid")
        if not centroid:
            return None
        features = self.extract_features_from_wav(wav_path)
        if not features:
            return None
        return self.similarity(features, centroid)

    @staticmethod
    def _mean_vector(vectors: list[list[float]]) -> list[float]:
        if not vectors:
            return []
        n = min(len(v) for v in vectors)
        return [sum(v[i] for v in vectors) / len(vectors) for i in range(n)]

    @staticmethod
    def similarity(a: list[float], b: list[float]) -> float:
        """Cosine + distance, normalizado a 0..1.

        Es intencionalmente tolerante porque micrófono/volumen/distancia cambian.
        El umbral real se controla desde la UI.
        """
        n = min(len(a), len(b))
        if n <= 0:
            return 0.0
        va = a[:n]
        vb = b[:n]
        dot = sum(x * y for x, y in zip(va, vb))
        na = math.sqrt(sum(x * x for x in va)) or 1e-9
        nb = math.sqrt(sum(y * y for y in vb)) or 1e-9
        cosine = max(-1.0, min(1.0, dot / (na * nb)))
        # distancia media suave para penalizar perfiles muy distintos
        dist = sum(abs(x - y) for x, y in zip(va, vb)) / n
        dist_score = math.exp(-2.2 * dist)
        return max(0.0, min(1.0, 0.70 * ((cosine + 1.0) / 2.0) + 0.30 * dist_score))

    @staticmethod
    def extract_features_from_wav(wav_path: str) -> list[float]:
        """Extrae una huella vocal barata: energía por bandas + ZCR + dinámica.

        Usa solo stdlib + numpy, que ya está instalado para sounddevice. Evita
        pyannote/speechbrain porque serían demasiado pesados para este proyecto.
        """
        if not wav_path or not Path(wav_path).exists():
            return []
        try:
            import numpy as np  # type: ignore
            with wave.open(str(wav_path), "rb") as wf:
                sr = wf.getframerate()
                channels = wf.getnchannels()
                raw = wf.readframes(wf.getnframes())
            if not raw:
                return []
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                audio = audio.reshape(-1, channels).mean(axis=1)
            audio = np.nan_to_num(audio)
            if audio.size < int(sr * 0.25):
                return []
            # Quita silencio extremo y normaliza volumen.
            abs_audio = np.abs(audio)
            gate = max(0.012, float(np.percentile(abs_audio, 65)) * 0.55)
            voiced = audio[abs_audio >= gate]
            if voiced.size < int(sr * 0.18):
                voiced = audio
            voiced = voiced - float(np.mean(voiced))
            peak = float(np.max(np.abs(voiced))) or 1.0
            voiced = voiced / peak

            # Limita duración para costo estable.
            max_len = int(sr * 3.0)
            if voiced.size > max_len:
                voiced = voiced[:max_len]

            rms = float(np.sqrt(np.mean(np.square(voiced))))
            zcr = float(np.mean(np.abs(np.diff(np.signbit(voiced).astype(np.int8))))) if voiced.size > 2 else 0.0

            # Espectro promedio.
            win = min(4096, max(1024, int(sr * 0.18)))
            hop = win // 2
            frames = []
            for start in range(0, max(1, voiced.size - win), hop):
                chunk = voiced[start:start + win]
                if chunk.size < win:
                    break
                chunk = chunk * np.hanning(win)
                spec = np.abs(np.fft.rfft(chunk)) + 1e-9
                frames.append(spec)
            if not frames:
                spec = np.abs(np.fft.rfft(voiced * np.hanning(voiced.size))) + 1e-9
            else:
                spec = np.mean(np.vstack(frames), axis=0)
            freqs = np.fft.rfftfreq((len(spec) - 1) * 2, d=1.0 / sr)
            total = float(np.sum(spec)) or 1e-9
            centroid = float(np.sum(freqs * spec) / total) / max(1.0, sr / 2.0)
            cumsum = np.cumsum(spec)
            rolloff_idx = int(np.searchsorted(cumsum, total * 0.85))
            rolloff = float(freqs[min(rolloff_idx, len(freqs)-1)]) / max(1.0, sr / 2.0)

            # Bandas fijas de voz humana. Log-ratios reducen efecto del volumen.
            bands = [(80,180),(180,300),(300,500),(500,800),(800,1200),(1200,1800),(1800,2600),(2600,3800),(3800,5200),(5200,7200)]
            energies = []
            for lo, hi in bands:
                mask = (freqs >= lo) & (freqs < hi)
                val = float(np.sum(spec[mask])) / total if np.any(mask) else 0.0
                energies.append(math.log1p(val * 20.0))
            # Delta simple entre bandas para timbre.
            deltas = [energies[i+1] - energies[i] for i in range(len(energies)-1)]
            return [rms, zcr, centroid, rolloff, *energies, *deltas]
        except Exception:
            return []
