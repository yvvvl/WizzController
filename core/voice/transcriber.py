from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    language: str | None = None
    duration: float | None = None


class WhisperTranscriber:
    """Wrapper lazy para faster-whisper.

    Fase 15 agrega límites de CPU para segundo plano. En juegos, la clave es
    que Whisper no use todos los hilos disponibles. `cpu_threads=1` es más lento,
    pero roba mucho menos FPS.
    """

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        *,
        cpu_threads: int = 1,
        num_workers: int = 1,
    ) -> None:
        self.model_size = model_size or "tiny"
        self.device = device or "cpu"
        self.compute_type = compute_type or "int8"
        self.cpu_threads = max(1, min(8, int(cpu_threads or 1)))
        self.num_workers = max(1, min(4, int(num_workers or 1)))
        self._model: Any = None

    @staticmethod
    def dependency_status() -> tuple[bool, str]:
        try:
            import faster_whisper  # type: ignore  # noqa: F401
            return True, "faster-whisper disponible"
        except Exception as exc:
            return False, f"Falta faster-whisper: {exc}"

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Falta faster-whisper. Ejecuta: python -m pip install faster-whisper"
            ) from exc
        _LOG.info(
            "[Voice] Cargando modelo %s (%s/%s, threads=%s, workers=%s)",
            self.model_size,
            self.device,
            self.compute_type,
            self.cpu_threads,
            self.num_workers,
        )
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            cpu_threads=self.cpu_threads,
            num_workers=self.num_workers,
        )

    def unload(self) -> None:
        """Libera referencia al modelo. Python/ctranslate2 liberará memoria después."""
        self._model = None

    def transcribe(
        self,
        wav_path: str,
        language: str | None = "es",
        vad_filter: bool = True,
        *,
        beam_size: int = 1,
        initial_prompt: str | None = None,
        keep_file: bool = False,
    ) -> TranscriptionResult:
        if not wav_path:
            return TranscriptionResult(text="", language=language or None, duration=0.0)
        self.load()
        assert self._model is not None
        beam_size = max(1, min(5, int(beam_size or 1)))
        # language=None permite autodetección. Para segundo plano seguimos recomendando "es"
        # porque evita que Whisper se vaya a idiomas raros con frases cortas. Para PTT se
        # puede usar modo mixto/auto si el usuario mezcla mucho inglés.
        language_arg = None if language in (None, "", "auto", "mixed") else str(language)
        segments, info = self._model.transcribe(
            wav_path,
            language=language_arg,
            task="transcribe",
            vad_filter=bool(vad_filter),
            vad_parameters={"min_silence_duration_ms": 450},
            beam_size=beam_size,
            condition_on_previous_text=False,
            no_speech_threshold=0.78,
            temperature=0.0,
            compression_ratio_threshold=1.9,
            log_prob_threshold=-1.0,
            initial_prompt=initial_prompt or None,
        )
        text = " ".join(seg.text.strip() for seg in segments if getattr(seg, "text", "").strip()).strip()
        if not keep_file:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass
        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None),
            duration=getattr(info, "duration", None),
        )
