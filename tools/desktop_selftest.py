from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import os
import platform
import sys
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_meta import APP_PRODUCT
from config.app_runtime_manager import AppRuntimeManager
from config.hotkeys_manager import HotkeysManager
from core.global_hotkeys import WindowsNativeHotkeyBackend


class _FakeWiz:
    state = {"dimming": 50}

    def get_state(self) -> dict[str, Any]:
        return dict(self.state)

    def __getattr__(self, name: str):
        def _noop(*args, **kwargs):
            print(f"[fake-wiz] {name}{args if args else ''}")
        return _noop


def _version(pkg: str) -> str:
    dist = {"PIL": "Pillow"}.get(pkg, pkg)
    try:
        return importlib.metadata.version(dist)
    except Exception:
        return "versión no detectada"


def _module_ok(name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(name)
        return True, _version(name)
    except Exception as exc:
        return False, str(exc)


def _print_check(label: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "--"
    print(f"[{mark}] {label}{': ' + detail if detail else ''}")


def _sleep_with_countdown(seconds: int) -> None:
    deadline = time.monotonic() + max(1, int(seconds))
    while time.monotonic() < deadline:
        left = int(round(deadline - time.monotonic()))
        print(f"  escuchando... {left:02d}s", end="\r", flush=True)
        time.sleep(0.25)
    print(" " * 32, end="\r")


def _listen(entries: list[dict[str, Any]], seconds: int) -> int:
    backend = WindowsNativeHotkeyBackend()
    if not backend.supported:
        print("[--] RegisterHotKey solo está disponible en Windows.")
        return 2
    fired = 0
    lock = threading.Lock()
    prepared: list[dict[str, Any]] = []
    for entry in entries:
        combo = str(entry.get("combo") or "").strip()
        label = str(entry.get("label") or combo)

        def _callback(label=label, combo=combo):
            nonlocal fired
            with lock:
                fired += 1
            print(f"\n[HOTKEY] {combo} -> {label}")

        prepared.append({"combo": combo, "callback": _callback})

    ok = backend.start(prepared)
    _print_check("RegisterHotKey iniciado", ok, f"registradas={backend.registered_count}")
    for err in backend.errors:
        print(f"[WARN] {err}")
    if not ok:
        return 1
    try:
        print("Presiona las combinaciones ahora. Ctrl+C cancela.")
        _sleep_with_countdown(seconds)
    except KeyboardInterrupt:
        print("\nCancelado por usuario.")
    finally:
        backend.stop()
    print(f"Disparos detectados: {fired}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico local de hotkeys globales y dependencias de bandeja WizZ.")
    parser.add_argument("--register-test", default="", help="Registra temporalmente una combinación de prueba. Ej: ctrl+alt+shift+f12")
    parser.add_argument("--listen-current", action="store_true", help="Escucha temporalmente las hotkeys configuradas usando RegisterHotKey nativo.")
    parser.add_argument("--seconds", type=int, default=12, help="Duración de escucha para --register-test/--listen-current.")
    args = parser.parse_args()

    print(f"{APP_PRODUCT} · diagnóstico hotkeys/tray")
    print("=" * 48)
    print(f"Python: {sys.version.split()[0]} · {sys.executable}")
    print(f"Sistema: {platform.platform()} · os.name={os.name}")
    print(f"Proyecto: {ROOT}")
    print()

    for mod, label in (("flet", "Flet"), ("pystray", "pystray/tray"), ("PIL", "Pillow/icono"), ("keyboard", "keyboard fallback/grabación")):
        ok, detail = _module_ok(mod)
        _print_check(label, ok, detail)

    runtime = AppRuntimeManager()
    print()
    print("Runtime:")
    for key in ("tray_enabled", "minimize_to_tray", "open_minimized", "startup_with_windows"):
        print(f"  {key}: {runtime.get(key)}")

    manager = HotkeysManager(_FakeWiz(), auto_apply=False)
    hotkeys = manager.get_hotkeys()
    print()
    print("Hotkeys:")
    print(f"  estado config: {'activadas' if manager.is_enabled() else 'desactivadas'}")
    print(f"  preferencia backend: {manager.backend_preference()}")
    print(f"  dependencia: {manager.dependency_message()}")
    print(f"  asignadas: {len(hotkeys)}")
    native_supported = WindowsNativeHotkeyBackend().supported
    _print_check("Backend nativo Windows", native_supported, "RegisterHotKey" if native_supported else "no aplica en este sistema")

    if hotkeys:
        print("  combos:")
        for aid, combo in sorted(hotkeys.items(), key=lambda x: x[0]):
            ok, msg = manager.validate_hotkey(combo)
            parsed = WindowsNativeHotkeyBackend.parse_combo(combo)
            native = "native-ok" if parsed else "native-no"
            print(f"    {combo:<24} -> {aid:<24} {msg} · {native}")

    print()
    tray_ready = runtime.get("tray_enabled", True) and _module_ok("pystray")[0] and _module_ok("PIL")[0]
    _print_check("Tray listo para iniciar", tray_ready, "requiere app corriendo para prueba visual")
    print("Tip: prueba visual real = python main.py, luego cerrar con X, restaurar desde bandeja, usar Salir.")

    if args.register_test:
        print()
        combo = HotkeysManager.normalize_hotkey(args.register_test)
        ok, msg = HotkeysManager.validate_hotkey(combo)
        _print_check(f"Combinación prueba {combo}", ok, msg)
        if not ok:
            return 1
        return _listen([{"combo": combo, "label": "prueba temporal"}], args.seconds)

    if args.listen_current:
        print()
        entries = [{"combo": combo, "label": manager.action_label(aid)} for aid, combo in hotkeys.items()]
        if not entries:
            print("No hay hotkeys configuradas para escuchar.")
            return 1
        return _listen(entries, args.seconds)

    print()
    print("Pruebas útiles:")
    print("  python tools/desktop_selftest.py --register-test ctrl+alt+shift+f12 --seconds 10")
    print("  python tools/desktop_selftest.py --listen-current --seconds 15")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
