from __future__ import annotations

import logging
from typing import Any, Callable

from .base_manager import JsonManager
from .favorites_manager import FavoritesManager

try:
    import keyboard as _keyboard  # type: ignore
except Exception as exc:  # pragma: no cover
    _keyboard = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

_LOG = logging.getLogger(__name__)


class HotkeysManager(JsonManager):
    """Atajos globales robustos.

    - No rompe la app si `keyboard` falta o el SO bloquea hooks.
    - No usa `unhook_all()` global; solo elimina los hooks propios.
    - Usa `dimming`, no `brightness`.
    - Favoritos por ID estable.
    """

    def __init__(self, wiz_controller, auto_apply: bool = True):
        super().__init__("hotkeys.json", default_data={"enabled": False, "suppress": False, "hotkeys": {}})
        if not isinstance(self.data, dict):
            self.data = {"enabled": False, "suppress": False, "hotkeys": {}}
            self.save()
        self.data.setdefault("enabled", False)
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
        return bool(self.data.get("enabled", False))

    def set_enabled(self, enabled: bool) -> None:
        self.data["enabled"] = bool(enabled)
        self.save()
        self.apply_hooks()

    def set_suppress(self, suppress: bool) -> None:
        self.data["suppress"] = bool(suppress)
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
            if key_combination and key == key_combination and aid != action_id:
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
            elif action_id == "bri_up":
                current = int(self.wiz.get_state().get("dimming", 50))
                self.wiz.set_brightness(min(100, current + 10))
            elif action_id == "bri_down":
                current = int(self.wiz.get_state().get("dimming", 50))
                self.wiz.set_brightness(max(10, current - 10))
            elif action_id == "white_warm":
                self.wiz.set_white_percent(0)
            elif action_id == "white_neutral":
                self.wiz.set_white(4000)
            elif action_id == "white_cold":
                self.wiz.set_white_percent(100)
            elif action_id.startswith("color_"):
                colors = {
                    "color_red": (255, 0, 0),
                    "color_green": (0, 255, 0),
                    "color_blue": (0, 0, 255),
                    "color_cyan": (0, 255, 255),
                    "color_magenta": (255, 0, 255),
                    "color_orange": (255, 127, 0),
                }
                if action_id in colors:
                    self.wiz.set_rgb(*colors[action_id])
            elif action_id.startswith("scene_"):
                self.wiz.set_scene(int(action_id.split("_", 1)[1]))
            elif action_id.startswith("fav_"):
                self._execute_favorite(action_id.split("_", 1)[1])
        except Exception as exc:
            self.last_error = str(exc)
            _LOG.debug("Hotkey action falló: %s", action_id, exc_info=True)

    def _execute_favorite(self, uid: str) -> None:
        self.fav_manager = FavoritesManager()
        fav = self.fav_manager.get_favorite(uid)
        if fav:
            self.wiz.apply_favorite(fav)
