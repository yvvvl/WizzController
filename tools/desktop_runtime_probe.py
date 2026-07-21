"""Prueba aislada de hotkeys globales y bandeja del sistema.

Uso recomendado en Windows, con la app cerrada:

    python tools/desktop_runtime_probe.py

Qué valida:
- que HotkeysManager puede registrar las combinaciones actuales;
- si el backend activo es RegisterHotKey nativo o fallback keyboard;
- que el icono de bandeja abre menú y responde a callbacks de pystray.

No controla ampolletas reales: usa un DummyWiz que solo imprime acciones.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config.hotkeys_manager import HotkeysManager  # noqa: E402


@dataclass
class DummyWiz:
    state: dict[str, Any] = field(default_factory=lambda: {"state": False, "dimming": 50})
    calls: list[str] = field(default_factory=list)

    def _log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        self.calls.append(line)
        print(line, flush=True)

    def turn_on(self) -> None:
        self.state["state"] = True
        self._log("turn_on()")

    def turn_off(self) -> None:
        self.state["state"] = False
        self._log("turn_off()")

    def toggle(self) -> None:
        self.state["state"] = not bool(self.state.get("state"))
        self._log(f"toggle() -> {'ON' if self.state['state'] else 'OFF'}")

    def reset_light(self) -> None:
        self.state.update({"state": True, "dimming": 100, "temp": 4000})
        self._log("reset_light()")

    def set_target_mode(self, mode: str) -> None:
        self._log(f"set_target_mode({mode!r})")

    def set_brightness(self, pct: int) -> None:
        self.state["dimming"] = max(10, min(100, int(pct)))
        self._log(f"set_brightness({self.state['dimming']}%)")

    def set_rgb(self, r: int, g: int, b: int) -> None:
        self.state.update({"r": int(r), "g": int(g), "b": int(b)})
        self._log(f"set_rgb({int(r)}, {int(g)}, {int(b)})")

    def set_white(self, kelvin: int) -> None:
        self.state["temp"] = int(kelvin)
        self._log(f"set_white({int(kelvin)}K)")

    def set_white_percent(self, pct: int) -> None:
        kelvin = round(2200 + (6500 - 2200) * max(0, min(100, int(pct))) / 100)
        self.set_white(kelvin)

    def set_scene(self, scene_id: int, speed: int | None = None) -> None:
        self.state.update({"sceneId": int(scene_id), "speed": speed})
        self._log(f"set_scene(sceneId={int(scene_id)}, speed={speed})")

    def get_state(self) -> dict[str, Any]:
        return dict(self.state)


def _make_probe_icon():
    from PIL import Image, ImageDraw  # type: ignore

    img = Image.new("RGBA", (64, 64), (13, 19, 38, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((8, 8, 56, 56), radius=15, fill=(16, 23, 45, 255), outline=(91, 140, 255, 255), width=3)
    draw.ellipse((19, 14, 45, 40), fill=(255, 255, 255, 255))
    draw.rounded_rectangle((25, 38, 39, 51), radius=4, fill=(0, 213, 255, 255))
    return img


def start_tray_probe(wiz: DummyWiz):
    try:
        import pystray  # type: ignore
    except Exception as exc:
        print(f"[Tray probe] pystray no disponible: {exc}")
        return None

    def ping(icon, item):
        wiz._log("tray ping")

    def fake_color(icon, item):
        wiz.set_rgb(0, 213, 255)

    def stop(icon, item):
        wiz._log("tray stop solicitado")
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("WizZ Probe activo", lambda icon, item: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Ping consola", ping),
        pystray.MenuItem("Color probe", fake_color),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir probe", stop),
    )
    icon = pystray.Icon("WizZProbe", _make_probe_icon(), "WizZ Probe", menu=menu)
    if hasattr(icon, "run_detached"):
        icon.run_detached()
    else:
        th = threading.Thread(target=icon.run, name="WizZProbeTray", daemon=True)
        th.start()
    print("[Tray probe] icono iniciado. Revisa el menú desde la bandeja.")
    return icon


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba local de hotkeys globales y tray sin abrir Flet ni controlar luces reales.")
    parser.add_argument("--seconds", type=int, default=0, help="Cierra automáticamente después de N segundos. 0 = esperar Ctrl+C.")
    parser.add_argument("--no-tray", action="store_true", help="Solo prueba hotkeys.")
    args = parser.parse_args()

    print("WizZ desktop runtime probe")
    print("Cierra la app real antes de correr esto, para no duplicar hotkeys.")
    print()

    wiz = DummyWiz()
    manager = HotkeysManager(wiz, auto_apply=True)
    print(f"Hotkeys backend: {manager.backend_status()}")
    print(f"Dependencias: {manager.dependency_message()}")
    if manager.last_warning:
        print(f"Warning: {manager.last_warning}")
    if manager.last_error:
        print(f"Error: {manager.last_error}")
    print("Hotkeys configuradas:")
    for row in manager.configured_rows():
        print(f"  - {row['combo']:<18} -> {row['name']}")
    print()

    icon = None if args.no_tray else start_tray_probe(wiz)
    print("Pulsa tus hotkeys y mira la consola. Ctrl+C para salir.")

    deadline = time.time() + args.seconds if args.seconds > 0 else None
    try:
        while deadline is None or time.time() < deadline:
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nCerrando probe...")
    finally:
        try:
            manager.stop()
        except Exception:
            pass
        try:
            if icon is not None:
                icon.stop()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
