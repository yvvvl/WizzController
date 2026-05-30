from __future__ import annotations

import logging
import threading
import time
from typing import Any

_LOG = logging.getLogger(__name__)
_SEQUENCE_LOCK = threading.Lock()  # Phase 39: cola ligera de rutinas


class ActionSequenceExecutor:
    """Motor único de acciones para rutinas, voz, hotkeys y favoritos compuestos.

    Diseño:
    - Python puro, sin Flet.
    - No agenda por hora.
    - Por defecto ejecuta en thread para no bloquear UI/hotkeys.
    - Las acciones WiZ siguen siendo fire-and-forget; solo `wait` duerme.
    """

    def __init__(self, wiz) -> None:
        self.wiz = wiz

    def execute_routine(self, routine_id: str, threaded: bool = True) -> str:
        from config.routines_manager import RoutinesManager

        routine = RoutinesManager().get_routine(str(routine_id))
        if not routine:
            raise ValueError(f"Rutina no encontrada: {routine_id}")
        return self.execute(routine, threaded=threaded)

    def execute(self, sequence_or_routine: dict[str, Any] | list[dict[str, Any]], threaded: bool = True) -> str:
        actions = self._extract_actions(sequence_or_routine)
        name = self._extract_name(sequence_or_routine)
        if threaded:
            th = threading.Thread(target=self._execute_safe, args=(actions, name), daemon=True)
            th.start()
            return name
        return self._execute_safe(actions, name)

    def _extract_actions(self, sequence_or_routine: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        if isinstance(sequence_or_routine, list):
            return [a for a in sequence_or_routine if isinstance(a, dict)]
        if isinstance(sequence_or_routine, dict):
            if isinstance(sequence_or_routine.get("actions"), list):
                return [a for a in sequence_or_routine.get("actions", []) if isinstance(a, dict)]
            if sequence_or_routine.get("type") == "sequence" and isinstance(sequence_or_routine.get("value"), list):
                return [a for a in sequence_or_routine.get("value", []) if isinstance(a, dict)]
            return [sequence_or_routine]
        return []

    def _extract_name(self, obj: Any) -> str:
        if isinstance(obj, dict):
            return str(obj.get("name") or obj.get("title") or "Rutina")
        return "Rutina"

    def _execute_safe(self, actions: list[dict[str, Any]], name: str) -> str:
        # Phase 39: cola ligera. Evita que dos rutinas se mezclen si entran
        # por voz/hotkey casi al mismo tiempo. No bloquea la UI porque esto
        # normalmente corre en thread daemon.
        with _SEQUENCE_LOCK:
            labels: list[str] = []
            try:
                for action in actions:
                    labels.append(self.execute_action(action))
            except Exception as exc:
                _LOG.warning("Rutina %s falló: %s", name, exc, exc_info=True)
                raise
            return " + ".join([x for x in labels if x]) or name

    def execute_action(self, action: dict[str, Any]) -> str:
        kind = str(action.get("type") or action.get("kind") or "").strip()
        value = action.get("value")

        if not kind:
            return "Acción vacía"

        if kind == "wait":
            ms = int(value if value is not None else action.get("ms", 250))
            time.sleep(max(0, min(ms, 5000)) / 1000.0)
            return f"Esperar {ms}ms"

        if kind == "method":
            method_name = str(action.get("method") or value or "")
            method = getattr(self.wiz, method_name, None)
            if callable(method):
                method()
                return str(action.get("name") or method_name)
            raise RuntimeError(f"Método no disponible: {method_name}")

        if kind == "turn_on":
            self.wiz.turn_on()
            return "Encender"
        if kind == "turn_off":
            self.wiz.turn_off()
            return "Apagar"
        if kind == "toggle":
            self.wiz.toggle()
            return "Alternar"

        if kind == "target_mode":
            mode = str(value or action.get("mode") or "single")
            if hasattr(self.wiz, "set_target_mode"):
                self.wiz.set_target_mode(mode)
            elif hasattr(self.wiz, "set_control_mode"):
                self.wiz.set_control_mode(mode)
            return "Destino " + ("una" if mode == "single" else "todas")

        if kind == "brightness":
            pct = int(value if value is not None else action.get("percent", 50))
            self.wiz.set_brightness(max(10, min(100, pct)))
            return f"Brillo {pct}%"

        if kind == "brightness_delta":
            delta = int(value if value is not None else action.get("delta", 0))
            state = self.wiz.get_state() if hasattr(self.wiz, "get_state") else {}
            current = int(state.get("dimming", 50) or 50)
            self.wiz.set_brightness(max(10, min(100, current + delta)))
            return f"Brillo {delta:+d}"

        if kind == "rgb":
            r, g, b = self._parse_rgb(value if value is not None else action)
            self.wiz.set_rgb(r, g, b)
            return f"RGB #{r:02X}{g:02X}{b:02X}"

        if kind == "white_kelvin":
            kelvin = int(value if value is not None else action.get("kelvin", 4000))
            self.wiz.set_white(kelvin)
            return f"Blanco {kelvin}K"

        if kind == "white_percent":
            pct = int(value if value is not None else action.get("percent", 50))
            pct = max(0, min(100, pct))
            if hasattr(self.wiz, "set_white_percent"):
                self.wiz.set_white_percent(pct)
            elif hasattr(self.wiz, "kelvin_from_percent"):
                self.wiz.set_white(self.wiz.kelvin_from_percent(pct))
            else:
                self.wiz.set_white(4000)
            return f"Blanco {pct}%"

        if kind == "scene":
            if isinstance(value, dict):
                scene_id = int(value.get("sceneId", value.get("id", 18)))
                speed = value.get("speed")
            else:
                scene_id = int(value if value is not None else action.get("sceneId", 18))
                speed = action.get("speed")
            self.wiz.set_scene(scene_id, speed)
            return f"Escena {scene_id}"

        if kind == "favorite":
            from config.favorites_manager import FavoritesManager

            fav = FavoritesManager().get_favorite(str(value or action.get("id") or ""))
            if fav and hasattr(self.wiz, "apply_favorite"):
                self.wiz.apply_favorite(fav)
            elif fav:
                self._execute_favorite_fallback(fav)
            return f"Favorito {fav.get('name') if fav else ''}".strip()

        if kind == "custom_scene":
            from config.custom_scenes_manager import CustomScenesManager

            scene = CustomScenesManager().get_scene(str(value or action.get("id") or ""))
            if scene and hasattr(self.wiz, "apply_custom_scene"):
                self.wiz.apply_custom_scene(scene)
                return f"Escena {scene.get('name')}"
            return "Escena personalizada"

        raise RuntimeError(f"Tipo de acción no soportado: {kind}")

    def _parse_rgb(self, value: Any) -> tuple[int, int, int]:
        if isinstance(value, str):
            h = value.strip().lstrip("#")
            if len(h) == 6:
                return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            return int(value[0]), int(value[1]), int(value[2])
        if isinstance(value, dict):
            if "hex" in value:
                return self._parse_rgb(value["hex"])
            return int(value.get("r", 255)), int(value.get("g", 255)), int(value.get("b", 255))
        return 255, 0, 0

    def _execute_favorite_fallback(self, fav: dict[str, Any]) -> None:
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "rgb":
            self.execute_action({"type": "rgb", "value": value})
        elif ftype == "white":
            self.execute_action({"type": "white_kelvin", "value": int(value)})
        elif ftype == "scene":
            self.execute_action({"type": "scene", "value": value})
        elif ftype == "brightness":
            self.execute_action({"type": "brightness", "value": int(value)})
