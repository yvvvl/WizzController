from __future__ import annotations

import pathlib
import re
import sys


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding='utf-8')


def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def patch_voice_service(root: pathlib.Path) -> None:
    path = root / 'core' / 'voice' / 'voice_service.py'
    if not path.exists():
        print('[Phase39] voice_service.py no existe; omitido.')
        return
    text = read(path)
    if 'Phase 39: gobernador de recursos' in text:
        print('[Phase39] voice_service.py ya estaba parcheado.')
        return

    # Atributo para no iniciar múltiples warmups.
    old = '        self._non_wake_streak = 0\n'
    new = old + '        self._warmup_thread: threading.Thread | None = None  # Phase 39: warmup ASR en segundo plano\n'
    if old in text and 'self._warmup_thread' not in text:
        text = text.replace(old, new, 1)

    # Si cambia modelo de fondo mientras está corriendo, precargar de nuevo.
    old = '''        if any(k in kwargs for k in ("continuous_model_size", "device", "continuous_compute_type", "continuous_cpu_threads", "continuous_num_workers")):\n            self._transcriber_continuous = None\n'''
    new = '''        if any(k in kwargs for k in ("continuous_model_size", "device", "continuous_compute_type", "continuous_cpu_threads", "continuous_num_workers")):\n            self._transcriber_continuous = None\n            if self.is_continuous_running():\n                self._warmup_continuous_model_async()\n'''
    if old in text:
        text = text.replace(old, new, 1)

    # Insertar métodos de gobernador después de unload_models.
    marker = '    # ------------------------------------------------------------------ #\n    # Captura + transcripción\n'
    methods = r'''
    # ------------------------------------------------------------------ #
    # Phase 39: gobernador de recursos / punto dulce
    # ------------------------------------------------------------------ #
    def _set_background_thread_priority(self) -> None:
        """Baja prioridad SOLO del hilo de voz en Windows.

        No toca el proceso completo ni la UI. Si falla, es no-op.
        Reduce tirones cuando Whisper transcribe en segundo plano.
        """
        try:
            if not bool(self.config().get("continuous_background_thread_low_priority", True)):
                return
            import ctypes
            kernel32 = ctypes.windll.kernel32
            THREAD_MODE_BACKGROUND_BEGIN = 0x00010000
            THREAD_PRIORITY_BELOW_NORMAL = -1
            handle = kernel32.GetCurrentThread()
            if not kernel32.SetThreadPriority(handle, THREAD_MODE_BACKGROUND_BEGIN):
                kernel32.SetThreadPriority(handle, THREAD_PRIORITY_BELOW_NORMAL)
        except Exception:
            pass

    def _warmup_continuous_model_async(self) -> None:
        """Precarga el modelo de fondo sin bloquear la UI.

        Esto no aumenta precisión ni cambia comandos: solo evita que el primer
        comando tarde demasiado porque el modelo se está cargando justo ahí.
        """
        try:
            cfg = self.config()
            if not bool(cfg.get("continuous_warm_model", True)):
                return
            if self._transcriber_continuous is not None and getattr(self._transcriber_continuous, "_model", None) is not None:
                return
            if self._warmup_thread and self._warmup_thread.is_alive():
                return
        except Exception:
            return

        def worker() -> None:
            self._set_background_thread_priority()
            try:
                started = time.time()
                self.transcriber(continuous=True).load()
                _LOG.info("[Voice] Modelo de fondo precargado en %.2fs", time.time() - started)
            except Exception:
                _LOG.debug("[Voice] Warmup de modelo de fondo falló", exc_info=True)

        self._warmup_thread = threading.Thread(target=worker, daemon=True, name="WizZVoiceWarmup")
        self._warmup_thread.start()

'''
    if marker in text:
        text = text.replace(marker, methods + marker, 1)
    else:
        text += '\n\n' + methods

    # Iniciar warmup después de arrancar hilo continuo.
    old = '        self._continuous_thread.start()\n        return {"ok": True, "message": "Escucha continua activada"}\n'
    new = '        self._continuous_thread.start()\n        self._warmup_continuous_model_async()\n        return {"ok": True, "message": "Escucha continua activada"}\n'
    if old in text:
        text = text.replace(old, new, 1)

    # Bajar prioridad al hilo continuo inmediatamente al arrancar loop.
    old = '    def _continuous_loop(self) -> None:\n        self._emit({"event": "continuous_started", "ok": True, "message": "Escucha continua activa"})\n'
    new = '    def _continuous_loop(self) -> None:\n        # Phase 39: gobernador de recursos. Solo afecta este hilo.\n        self._set_background_thread_priority()\n        self._emit({"event": "continuous_started", "ok": True, "message": "Escucha continua activa"})\n'
    if old in text:
        text = text.replace(old, new, 1)

    # Mejorar load_model para permitir precargar modelo de fondo desde UI/arranque.
    old = '''    def load_model(self, *, continuous: bool = False) -> dict[str, Any]:\n        started = time.time()\n        self.transcriber(continuous=continuous).load()\n        kind = "segundo plano" if continuous else "push-to-talk"\n        return {"ok": True, "message": f"Modelo {kind} cargado", "elapsed": round(time.time() - started, 2)}\n'''
    new = '''    def load_model(self, *, continuous: bool = False) -> dict[str, Any]:\n        started = time.time()\n        if continuous:\n            self._set_background_thread_priority()\n        self.transcriber(continuous=continuous).load()\n        kind = "segundo plano" if continuous else "push-to-talk"\n        return {"ok": True, "message": f"Modelo {kind} cargado", "elapsed": round(time.time() - started, 2)}\n'''
    if old in text:
        text = text.replace(old, new, 1)

    # Marca para detectar parche.
    text = text.replace('class VoiceService:', 'class VoiceService:\n    # Phase 39: gobernador de recursos + warmup de modelo fondo', 1)
    write(path, text)
    print('[Phase39] voice_service.py optimizado.')


def patch_voice_config(root: pathlib.Path) -> None:
    path = root / 'config' / 'voice_config_manager.py'
    if not path.exists():
        print('[Phase39] voice_config_manager.py no existe; omitido.')
        return
    text = read(path)
    if 'continuous_warm_model' in text and 'continuous_background_thread_low_priority' in text:
        print('[Phase39] voice_config_manager.py ya tenía defaults de performance.')
        return
    insert = '''
        # Phase 39: punto dulce de performance.
        # Precargar modelo de fondo evita que el primer comando tarde demasiado.
        # Bajar prioridad del hilo de voz evita tirones sin sacrificar precisión.
        "continuous_warm_model": True,
        "continuous_background_thread_low_priority": True,
        "performance_governor_enabled": True,
'''
    target = '        "history_limit": 25,\n'
    if target in text:
        text = text.replace(target, insert + target, 1)
    else:
        text = text.replace('    DEFAULTS: dict[str, Any] = {', '    DEFAULTS: dict[str, Any] = {\n' + insert, 1)
    write(path, text)
    print('[Phase39] voice_config_manager.py actualizado.')


def patch_action_sequence(root: pathlib.Path) -> None:
    path = root / 'core' / 'action_sequence.py'
    if not path.exists():
        print('[Phase39] action_sequence.py no existe; omitido.')
        return
    text = read(path)
    if 'Phase 39: cola ligera de rutinas' in text:
        print('[Phase39] action_sequence.py ya estaba optimizado.')
        return
    # Agregar lock global para no superponer dos rutinas pesadas si voz/hotkey se pisan.
    if '_SEQUENCE_LOCK' not in text:
        text = text.replace('_LOG = logging.getLogger(__name__)\n', '_LOG = logging.getLogger(__name__)\n_SEQUENCE_LOCK = threading.Lock()  # Phase 39: cola ligera de rutinas\n', 1)
    old = '''    def _execute_safe(self, actions: list[dict[str, Any]], name: str) -> str:\n        labels: list[str] = []\n        try:\n            for action in actions:\n                labels.append(self.execute_action(action))\n        except Exception as exc:\n            _LOG.warning("Rutina %s falló: %s", name, exc, exc_info=True)\n            raise\n        return " + ".join([x for x in labels if x]) or name\n'''
    new = '''    def _execute_safe(self, actions: list[dict[str, Any]], name: str) -> str:\n        # Phase 39: cola ligera. Evita que dos rutinas se mezclen si entran\n        # por voz/hotkey casi al mismo tiempo. No bloquea la UI porque esto\n        # normalmente corre en thread daemon.\n        with _SEQUENCE_LOCK:\n            labels: list[str] = []\n            try:\n                for action in actions:\n                    labels.append(self.execute_action(action))\n            except Exception as exc:\n                _LOG.warning("Rutina %s falló: %s", name, exc, exc_info=True)\n                raise\n            return " + ".join([x for x in labels if x]) or name\n'''
    if old in text:
        text = text.replace(old, new, 1)
    write(path, text)
    print('[Phase39] action_sequence.py optimizado.')


def patch_voice_panel(root: pathlib.Path) -> None:
    path = root / 'ui' / 'components' / 'voice_panel.py'
    if not path.exists():
        print('[Phase39] voice_panel.py no existe; omitido.')
        return
    text = read(path)
    if 'Precargar fondo' in text or 'Modelo listo en segundo plano' in text:
        print('[Phase39] voice_panel.py ya tenía indicador de optimización.')
        return
    # Actualizar texto informativo sin cambiar layout fuerte.
    text = text.replace(
        'Punto dulce actual: activador al inicio, corte de silencio y filtro de ruido activos. Ej: pc apaga la luz.',
        'Punto dulce: activador al inicio + modelo de fondo precargado + hilo de voz en baja prioridad. Ej: pc apaga la luz.'
    )
    write(path, text)
    print('[Phase39] voice_panel.py actualizado.')


def main() -> None:
    root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd()
    patch_voice_service(root)
    patch_voice_config(root)
    patch_action_sequence(root)
    patch_voice_panel(root)


if __name__ == '__main__':
    main()
