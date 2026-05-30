from __future__ import annotations

import logging
from typing import Any, Callable

from .base_manager import JsonManager
from .favorites_manager import FavoritesManager
from .custom_scenes_manager import CustomScenesManager

try:
    import keyboard as _keyboard  # type: ignore
except Exception as exc:  # pragma: no cover
    _keyboard = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

_LOG = logging.getLogger(__name__)


class HotkeysManager(JsonManager):
    """Gestor robusto de atajos globales.

    - No revienta si `keyboard` no está instalado.
    - Guarda hotkeys por action_id.
    - Usa `dimming`, no `brightness`.
    - Favoritos por ID estable, no por nombre.
    """

    DEFAULT_HOTKEYS = {
        "toggle": "ctrl+alt+l",
        "bri_up": "ctrl+alt+up",
        "bri_down": "ctrl+alt+down",
    }

    def __init__(self, wiz_controller, auto_apply: bool = True):
        super().__init__(
            "hotkeys.json",
            default_data={"enabled": True, "suppress": False, "hotkeys": dict(self.DEFAULT_HOTKEYS)},
        )
        if not isinstance(self.data, dict):
            self.data = {"enabled": True, "suppress": False, "hotkeys": dict(self.DEFAULT_HOTKEYS)}
            self.save()
        self.data.setdefault("enabled", True)
        self.data.setdefault("suppress", False)
        self.data.setdefault("hotkeys", {})

        self.wiz = wiz_controller
        self.fav_manager = FavoritesManager()
        self._handles: list[Any] = []
        self.last_error: str | None = None
        if auto_apply:
            self.apply_hooks()

    @property
    def available(self) -> bool:
        return _keyboard is not None

    def is_enabled(self) -> bool:
        return bool(self.data.get("enabled", True))

    def enabled(self) -> bool:
        """Alias usado por HotkeysPanel."""
        return self.is_enabled()

    def set_enabled(self, enabled: bool) -> None:
        self.data["enabled"] = bool(enabled)
        self.save()
        self.apply_hooks()

    def get_hotkeys(self) -> dict[str, str]:
        hotkeys = self.data.get("hotkeys", {})
        return hotkeys if isinstance(hotkeys, dict) else {}

    def get_hotkey(self, action_id: str) -> str | None:
        return self.get_hotkeys().get(action_id)

    def set_hotkey(self, action_id: str, key_combination: str) -> None:
        key_combination = (key_combination or "").strip().lower()
        hotkeys = dict(self.get_hotkeys())
        for aid, key in list(hotkeys.items()):
            if key and key == key_combination:
                del hotkeys[aid]
        if key_combination:
            hotkeys[action_id] = key_combination
        else:
            hotkeys.pop(action_id, None)
        self.data["hotkeys"] = hotkeys
        self.save()
        self.apply_hooks()

    def clear_hotkey(self, action_id: str) -> None:
        self.set_hotkey(action_id, "")

    def set_suppress(self, suppress: bool) -> None:
        self.data["suppress"] = bool(suppress)
        self.save()
        self.apply_hooks()

    def remove_hotkey(self, action_id: str) -> None:
        self.clear_hotkey(action_id)

    def reset_defaults(self) -> None:
        self.data["enabled"] = True
        self.data["hotkeys"] = dict(self.DEFAULT_HOTKEYS)
        self.save()
        self.apply_hooks()

    def list_actions(self) -> list[dict[str, str]]:
        actions: list[dict[str, str]] = [
            {"id": "toggle", "name": "Alternar encendido", "group": "General"},
            {"id": "on", "name": "Encender", "group": "General"},
            {"id": "off", "name": "Apagar", "group": "General"},
            {"id": "reset", "name": "Restaurar luz", "group": "General"},
            {"id": "target_single", "name": "Modo una ampolleta", "group": "Destino"},
            {"id": "target_all", "name": "Modo todas", "group": "Destino"},
            {"id": "bri_up", "name": "Brillo +10%", "group": "Brillo"},
            {"id": "bri_down", "name": "Brillo -10%", "group": "Brillo"},
            {"id": "bri_25", "name": "Brillo 25%", "group": "Brillo"},
            {"id": "bri_50", "name": "Brillo 50%", "group": "Brillo"},
            {"id": "bri_75", "name": "Brillo 75%", "group": "Brillo"},
            {"id": "bri_100", "name": "Brillo 100%", "group": "Brillo"},
            {"id": "white_warm", "name": "Blanco cálido", "group": "Blancos"},
            {"id": "white_neutral", "name": "Blanco neutro", "group": "Blancos"},
            {"id": "white_cold", "name": "Blanco frío", "group": "Blancos"},
            {"id": "white_0", "name": "Blanco 0% del rango", "group": "Blancos"},
            {"id": "white_25", "name": "Blanco 25% del rango", "group": "Blancos"},
            {"id": "white_50", "name": "Blanco 50% del rango", "group": "Blancos"},
            {"id": "white_75", "name": "Blanco 75% del rango", "group": "Blancos"},
            {"id": "white_100", "name": "Blanco 100% del rango", "group": "Blancos"},
            {"id": "color_red", "name": "Rojo", "group": "Colores"},
            {"id": "color_green", "name": "Verde", "group": "Colores"},
            {"id": "color_blue", "name": "Azul", "group": "Colores"},
            {"id": "color_cyan", "name": "Cian", "group": "Colores"},
            {"id": "color_magenta", "name": "Magenta", "group": "Colores"},
            {"id": "color_orange", "name": "Naranjo", "group": "Colores"},
            {"id": "color_pink", "name": "Rosa", "group": "Colores"},
            {"id": "color_yellow", "name": "Amarillo", "group": "Colores"},
            {"id": "color_custom", "name": "Color personalizado", "group": "Colores"},
        ]
        # Hotkeys de colores personalizados guardados como color_hex_ff00aa.
        # Se agregan dinámicamente para que la lista muestre nombres legibles.
        try:
            for aid in self.get_hotkeys().keys():
                if isinstance(aid, str) and aid.startswith("color_hex_"):
                    raw = aid.removeprefix("color_hex_")[:6]
                    if len(raw) == 6:
                        actions.append({"id": aid, "name": f"Color #{raw.upper()}", "group": "Colores personalizados"})
        except Exception:
            pass

        try:
            from core import wiz_scenes
            for scene in wiz_scenes.CATALOG.values():
                actions.append({"id": f"scene_{scene.id}", "name": scene.name, "group": "Escenas WiZ"})
        except Exception:
            pass

        self.fav_manager = FavoritesManager()
        for fav in self.fav_manager.get_favorites():
            uid = fav.get("id")
            if uid:
                actions.append({"id": f"fav_{uid}", "name": fav.get("name", "Favorito"), "group": "Favoritos"})

        try:
            custom = CustomScenesManager()
            for scene in custom.get_scenes():
                uid = scene.get("id")
                if uid:
                    actions.append({"id": f"custom_{uid}", "name": scene.get("name", "Mi escena"), "group": "Mis escenas"})
        except Exception:
            pass
        return actions

    def _clear_hooks(self) -> None:
        if _keyboard is None:
            self._handles.clear()
            return
        for handle in self._handles:
            try:
                _keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._handles.clear()

    def apply_hooks(self) -> None:
        self._clear_hooks()
        self.last_error = None

        if not self.is_enabled():
            return
        if _keyboard is None:
            self.last_error = f"keyboard no disponible: {_IMPORT_ERROR}"
            return

        suppress = bool(self.data.get("suppress", False))
        for action_id, keys in self.get_hotkeys().items():
            if not keys:
                continue
            cb = self._create_callback(action_id)
            if not cb:
                continue
            try:
                handle = _keyboard.add_hotkey(keys, cb, suppress=suppress, trigger_on_release=False)
                self._handles.append(handle)
            except Exception as exc:
                self.last_error = str(exc)
                _LOG.warning("No pude registrar hotkey %s=%s: %s", action_id, keys, exc)

    def read_hotkey_blocking(self) -> str | None:
        if _keyboard is None:
            self.last_error = f"keyboard no disponible: {_IMPORT_ERROR}"
            return None
        try:
            return _keyboard.read_hotkey(suppress=False)
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def _create_callback(self, action_id: str) -> Callable[[], None] | None:
        return lambda: self.execute_action(action_id)

    def execute_action(self, action_id: str) -> None:
        try:
            if action_id == "toggle":
                self.wiz.toggle()
            elif action_id == "on":
                self.wiz.turn_on()
            elif action_id == "off":
                self.wiz.turn_off()
            elif action_id == "reset":
                self.wiz.reset_light()
            elif action_id == "target_single":
                self.wiz.set_target_mode("single")
            elif action_id == "target_all":
                self.wiz.set_target_mode("all")
            elif action_id == "bri_up":
                current = int(self.wiz.get_state().get("dimming", 50))
                self.wiz.set_brightness(min(100, current + 10))
            elif action_id == "bri_down":
                current = int(self.wiz.get_state().get("dimming", 50))
                self.wiz.set_brightness(max(10, current - 10))
            elif action_id.startswith("bri_") and action_id[4:].isdigit():
                self.wiz.set_brightness(int(action_id[4:]))
            elif action_id == "white_warm":
                self.wiz.set_white_percent(10)
            elif action_id == "white_neutral":
                self.wiz.set_white(4000)
            elif action_id == "white_cold":
                self.wiz.set_white_percent(100)
            elif action_id.startswith("white_") and action_id[6:].isdigit():
                self.wiz.set_white_percent(int(action_id[6:]))
            elif action_id.startswith("color_hex_"):
                h = action_id.removeprefix("color_hex_")[:6]
                if len(h) == 6:
                    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                    self.wiz.set_rgb(r, g, b)
            elif action_id.startswith("color_"):
                colors = {
                    "color_red": (255, 0, 0),
                    "color_green": (0, 255, 0),
                    "color_blue": (0, 0, 255),
                    "color_cyan": (0, 255, 255),
                    "color_magenta": (255, 0, 255),
                    "color_orange": (255, 127, 0),
                    "color_pink": (255, 64, 160),
                    "color_yellow": (255, 208, 0),
                }
                if action_id in colors:
                    self.wiz.set_rgb(*colors[action_id])
            elif action_id.startswith("scene_"):
                self.wiz.set_scene(int(action_id.split("_", 1)[1]))
            elif action_id.startswith("fav_"):
                self._execute_favorite(action_id.split("_", 1)[1])
            elif action_id.startswith("custom_"):
                self._execute_custom_scene(action_id.split("_", 1)[1])
        except Exception as exc:
            self.last_error = str(exc)
            _LOG.debug("Hotkey action falló: %s", action_id, exc_info=True)

    def _execute_favorite(self, uid: str) -> None:
        self.fav_manager = FavoritesManager()
        fav = self.fav_manager.get_favorite(uid)
        if not fav:
            return
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "rgb":
            h = str(value).lstrip("#")
            if len(h) == 6:
                self.wiz.set_rgb(*(int(h[i:i + 2], 16) for i in (0, 2, 4)))
        elif ftype == "white":
            self.wiz.set_white(int(value))
        elif ftype == "scene":
            if isinstance(value, dict):
                self.wiz.set_scene(int(value.get("sceneId", 1)), value.get("speed"))
            else:
                self.wiz.set_scene(int(value))
        elif ftype == "brightness":
            self.wiz.set_brightness(int(value))

    def _execute_custom_scene(self, uid: str) -> None:
        scene = CustomScenesManager().get_scene(uid)
        if not scene:
            return
        mode = scene.get("mode")
        value = scene.get("value") or {}
        if mode == "rgb" and isinstance(value, dict):
            self.wiz.set_rgb(int(value.get("r", 255)), int(value.get("g", 255)), int(value.get("b", 255)))
            if "dimming" in value:
                self.wiz.set_brightness(int(value.get("dimming", 100)))
        elif mode == "white" and isinstance(value, dict):
            self.wiz.set_white(int(value.get("temp", 4000)))
            if "dimming" in value:
                self.wiz.set_brightness(int(value.get("dimming", 100)))
        elif mode == "scene" and isinstance(value, dict):
            self.wiz.set_scene(int(value.get("sceneId", 18)), value.get("speed"))
            if "dimming" in value:
                self.wiz.set_brightness(int(value.get("dimming", 100)))

# ---------------------------------------------------------------------------
# Phase 38: Rutinas compuestas en Hotkeys.
# Extensión no invasiva para no romper el panel existente.
# ---------------------------------------------------------------------------
try:
    from config.routines_manager import RoutinesManager as _Phase38RoutinesManager
    from core.action_sequence import ActionSequenceExecutor as _Phase38ActionSequenceExecutor

    if not hasattr(HotkeysManager, "_phase38_routines_patch"):
        _phase38_orig_list_actions = HotkeysManager.list_actions
        _phase38_orig_execute_action = HotkeysManager.execute_action

        def _phase38_list_actions(self):
            actions = list(_phase38_orig_list_actions(self))
            try:
                for routine in _Phase38RoutinesManager().get_routines():
                    uid = routine.get("id")
                    if uid:
                        actions.append({
                            "id": f"routine_{uid}",
                            "name": routine.get("name", "Rutina"),
                            "group": "Rutinas",
                        })
            except Exception:
                pass
            return actions

        def _phase38_execute_action(self, action_id: str) -> None:
            if isinstance(action_id, str) and action_id.startswith("routine_"):
                uid = action_id.split("_", 1)[1]
                _Phase38ActionSequenceExecutor(self.wiz).execute_routine(uid, threaded=True)
                return
            return _phase38_orig_execute_action(self, action_id)

        HotkeysManager.list_actions = _phase38_list_actions
        HotkeysManager.execute_action = _phase38_execute_action
        HotkeysManager._phase38_routines_patch = True
except Exception:
    pass
