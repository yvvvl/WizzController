from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[0]
# When copied to <repo>/tools, parents[1] is the project root. When executed
# elsewhere, fall back to the current working directory.
project_root = Path.cwd().resolve()
if (project_root / "core").is_dir():
    root = project_root
elif len(Path(__file__).resolve().parents) > 1 and (Path(__file__).resolve().parents[1] / "core").is_dir():
    root = Path(__file__).resolve().parents[1]
else:
    raise SystemExit("Ejecuta este probe desde la raíz de WizzController.")

if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.light_controller import LightController  # noqa: E402


def _keys(value: Any) -> list[str]:
    return sorted(str(key) for key in (value or {}).keys()) if isinstance(value, dict) else []


def snapshot(controller: LightController, label: str, ip: str) -> dict[str, Any]:
    proto = getattr(controller, "proto", None)
    config = getattr(controller, "config", None)
    manager = getattr(controller, "bulbs_manager", None)

    try:
        details = controller.get_bulbs_detailed()
    except Exception as exc:  # pragma: no cover - diagnostic
        details = [{"error": repr(exc)}]

    try:
        target_config = controller.get_target_config()
    except Exception as exc:  # pragma: no cover - diagnostic
        target_config = {"error": repr(exc)}

    try:
        removed = config.get("removed_bulbs", []) if config is not None else None
    except Exception as exc:  # pragma: no cover - diagnostic
        removed = {"error": repr(exc)}

    try:
        saved = manager.get_bulbs() if manager is not None else {}
    except Exception as exc:  # pragma: no cover - diagnostic
        saved = {"error": repr(exc)}

    return {
        "label": label,
        "time": round(time.time(), 3),
        "tested_ip": ip,
        "bulb_ips": sorted(str(item) for item in getattr(controller, "bulb_ips", set())),
        "live_bulbs": _keys(getattr(controller, "bulbs", {})),
        "saved_bulbs": _keys(saved),
        "proto_discovered": _keys(getattr(proto, "discovered", {})),
        "proto_last_pilot": _keys(getattr(proto, "last_pilot", {})),
        "removed_bulbs": removed,
        "active_ip": target_config.get("active_ip") if isinstance(target_config, dict) else None,
        "targets": target_config.get("targets") if isinstance(target_config, dict) else None,
        "detailed_ips": [
            item.get("ip")
            for item in details
            if isinstance(item, dict) and item.get("ip")
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce y diagnostica la eliminación de una ampolleta activa después de usarla."
    )
    parser.add_argument("--ip", help="IP a probar. Si se omite, usa la primera detectada.")
    parser.add_argument("--wait", type=float, default=7.0, help="Espera inicial de discovery.")
    args = parser.parse_args()

    controller = LightController()
    controller.start()
    try:
        deadline = time.time() + max(2.0, args.wait)
        items: list[dict[str, Any]] = []
        while time.time() < deadline:
            try:
                items = controller.get_bulbs_detailed()
            except Exception:
                items = []
            if items:
                break
            time.sleep(0.25)

        ip = str(args.ip or (items[0].get("ip") if items else "") or "").strip()
        if not ip:
            print("No se encontró ninguna ampolleta. Aborta sin modificar configuración.")
            return 2

        print(f"Probando eliminación activa de {ip}")
        if hasattr(controller, "set_active_bulb"):
            controller.set_active_bulb(ip)

        state = controller.get_state() if hasattr(controller, "get_state") else {}
        brightness = int((state or {}).get("dimming", 50) or 50)
        brightness = max(10, min(100, brightness))

        # Genera exactamente la condición problemática: uso reciente + verificaciones
        # post-acción pendientes, sin cambiar perceptiblemente el brillo.
        controller.set_brightness(brightness)
        time.sleep(0.08)

        reports = [snapshot(controller, "antes_de_eliminar", ip)]
        controller.remove_bulb(ip)
        reports.append(snapshot(controller, "inmediato", ip))

        for delay in (0.20, 0.50, 1.00, 2.00, 4.00):
            time.sleep(delay)
            reports.append(snapshot(controller, f"despues_{delay:.2f}s", ip))

        print(json.dumps(reports, ensure_ascii=False, indent=2, default=str))

        last = reports[-1]
        resurrected_in = {
            "bulb_ips": ip in last["bulb_ips"],
            "live_bulbs": ip in last["live_bulbs"],
            "saved_bulbs": ip in last["saved_bulbs"],
            "proto_discovered": ip in last["proto_discovered"],
            "proto_last_pilot": ip in last["proto_last_pilot"],
            "detailed_ips": ip in last["detailed_ips"],
            "active_ip": last["active_ip"] == ip,
            "targets": ip in (last["targets"] or []),
        }
        failures = [name for name, present in resurrected_in.items() if present]
        print("\nRESULTADO")
        if failures:
            print("FALLO: la ampolleta reapareció en: " + ", ".join(failures))
            return 1
        print("OK: la ampolleta permaneció eliminada durante toda la observación.")
        return 0
    finally:
        try:
            controller.stop()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
