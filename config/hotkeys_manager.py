from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Any, Callable

from .base_manager import JsonManager
from .custom_scenes_manager import CustomScenesManager
from .favorites_manager import FavoritesManager
from core.global_hotkeys import WindowsNativeHotkeyBackend
from localization import (
    LocalizationManager,
    translated_default_routine_name,
    translated_favorite_name,
    translated_scene_name,
)

try:
    import keyboard as _keyboard  # type: ignore
except Exception as exc:  # pragma: no cover - depende del SO/permisos
    _keyboard = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

_LOG = logging.getLogger(__name__)


class HotkeysManager(JsonManager):
    """Gestor de hotkeys globales para WizZ Controller.

    Objetivo de esta versión:
    - Un solo camino de ejecución: ActionSequenceExecutor.
    - Sin monkey-patches al final del archivo.
    - No usa unhook_all(): solo remueve los handles que registró esta app.
    - Funciona aunque `keyboard` no esté instalado o Windows bloquee hooks.
    - Evita hotkeys peligrosas y repeticiones por tecla mantenida.
    - Soporta acciones estáticas, escenas WiZ, favoritos, escenas custom y rutinas.
    """

    DEFAULT_HOTKEYS: dict[str, str] = {
        "toggle": "ctrl+alt+l",
        "bri_up": "ctrl+alt+up",
        "bri_down": "ctrl+alt+down",
    }

    DEFAULT_DATA: dict[str, Any] = {
        "enabled": True,
        "suppress": False,
        "trigger_on_release": True,
        "cooldown_ms": 280,
        # auto = Windows RegisterHotKey si está disponible; fallback a keyboard.
        # keyboard = fuerza el backend histórico de hooks.
        # native = exige RegisterHotKey en Windows y no cae a hooks.
        "backend": "auto",
        "hotkeys": dict(DEFAULT_HOTKEYS),
    }

    # Combinaciones que conviene bloquear. Algunas ni siquiera llegan a Python,
    # pero rechazarlas evita confusión y UX mala.
    RESERVED_COMBOS = {
        "alt+f4",
        "alt+tab",
        "ctrl+alt+del",
        "ctrl+alt+delete",
        "ctrl+shift+esc",
        "win+l",
        "win+d",
        "win+r",
        "win+tab",
        "win+e",
        "esc",
        "escape",
    }

    MODIFIERS = {"ctrl", "alt", "shift", "win"}

    def __init__(self, wiz_controller, auto_apply: bool = True, i18n=None):
        self.i18n = i18n or LocalizationManager(preference="es")
        super().__init__("hotkeys.json", default_data=dict(self.DEFAULT_DATA))
        self.wiz = wiz_controller
        self._handles: list[Any] = []
        self._hook_lock = threading.RLock()
        self._exec_lock = threading.Lock()
        self._last_exec: dict[str, float] = {}
        self._native_backend = WindowsNativeHotkeyBackend()
        self._executor = None
        self.last_error: str | None = None
        self.last_warning: str | None = None
        self.last_backend: str = "none"
        self._registration_report: dict[str, Any] = {
            "backend": "none",
            "total": 0,
            "native": 0,
            "keyboard": 0,
            "failed": [],
        }
        self._migrate()
        if auto_apply:
            self.apply_hooks()

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    # ------------------------------------------------------------------ #
    # Estado/config
    # ------------------------------------------------------------------ #
    def _migrate(self) -> None:
        if not isinstance(self.data, dict):
            self.data = dict(self.DEFAULT_DATA)
        changed = False
        for key, value in self.DEFAULT_DATA.items():
            if key not in self.data:
                self.data[key] = dict(value) if isinstance(value, dict) else value
                changed = True
        if not isinstance(self.data.get("hotkeys"), dict):
            self.data["hotkeys"] = dict(self.DEFAULT_HOTKEYS)
            changed = True

        # Normalizar combos guardadas sin perder acciones desconocidas.
        normalised: dict[str, str] = {}
        for aid, combo in self.data.get("hotkeys", {}).items():
            aid = str(aid or "").strip()
            if not aid:
                continue
            norm = self.normalize_hotkey(str(combo or ""))
            if norm:
                normalised[aid] = norm
        if normalised != self.data.get("hotkeys"):
            self.data["hotkeys"] = normalised
            changed = True
        if changed:
            self.save()

    @property
    def available(self) -> bool:
        """True si existe algún backend global utilizable."""
        return os.name == "nt" or _keyboard is not None

    @property
    def can_record(self) -> bool:
        """La grabación interactiva sigue usando la librería keyboard."""
        return _keyboard is not None

    def dependency_message(self) -> str:
        if os.name == "nt":
            if _keyboard is None:
                return self._t("hotkeys.dependency.native_recording_missing", error=_IMPORT_ERROR)
            return self._t("hotkeys.dependency.native_ready")
        if _keyboard is not None:
            return self._t("hotkeys.dependency.keyboard_ready")
        return self._t("hotkeys.dependency.keyboard_missing", error=_IMPORT_ERROR)

    def backend_preference(self) -> str:
        value = str(self.data.get("backend", "auto") or "auto").lower().strip()
        return value if value in {"auto", "native", "keyboard"} else "auto"

    def backend_status(self) -> str:
        if not self.is_enabled():
            return self._t("hotkeys.status.disabled")
        report = self.registration_report()
        total = int(report.get("total", 0) or 0)
        native = int(report.get("native", 0) or 0)
        keyboard = int(report.get("keyboard", 0) or 0)
        active = native + keyboard
        suffix = f" · {active}/{total}" if total else ""
        if self.last_backend == "windows":
            return self._t("hotkeys.status.native", suffix=suffix)
        if self.last_backend == "hybrid":
            return self._t("hotkeys.status.hybrid", suffix=suffix)
        if self.last_backend == "keyboard":
            return self._t("hotkeys.status.keyboard", suffix=suffix)
        if self.last_error:
            return self._t("hotkeys.status.unregistered")
        return self._t("hotkeys.status.empty") if not total else self._t("hotkeys.status.unregistered")

    def registration_report(self) -> dict[str, Any]:
        report = dict(self._registration_report)
        report["failed"] = [dict(row) for row in self._registration_report.get("failed", [])]
        return report

    def enabled(self) -> bool:
        return self.is_enabled()

    def is_enabled(self) -> bool:
        return bool(self.data.get("enabled", True))

    def set_enabled(self, enabled: bool) -> None:
        self.data["enabled"] = bool(enabled)
        self.save()
        self.apply_hooks()

    def suppress_enabled(self) -> bool:
        return bool(self.data.get("suppress", False))

    def set_suppress(self, suppress: bool) -> None:
        self.data["suppress"] = bool(suppress)
        self.save()
        self.apply_hooks()

    def trigger_on_release(self) -> bool:
        return bool(self.data.get("trigger_on_release", True))

    def set_trigger_on_release(self, enabled: bool) -> None:
        self.data["trigger_on_release"] = bool(enabled)
        self.save()
        self.apply_hooks()

    def cooldown_ms(self) -> int:
        try:
            return max(80, min(2000, int(self.data.get("cooldown_ms", 280))))
        except Exception:
            return 280

    def set_cooldown_ms(self, ms: int) -> None:
        try:
            self.data["cooldown_ms"] = max(80, min(2000, int(ms)))
        except Exception:
            self.data["cooldown_ms"] = 280
        self.save()

    def get_hotkeys(self) -> dict[str, str]:
        hotkeys = self.data.get("hotkeys", {})
        return dict(hotkeys) if isinstance(hotkeys, dict) else {}

    def get_hotkey(self, action_id: str) -> str | None:
        return self.get_hotkeys().get(str(action_id))

    # ------------------------------------------------------------------ #
    # Normalización/validación
    # ------------------------------------------------------------------ #
    @classmethod
    def normalize_hotkey(cls, combo: str) -> str:
        combo = str(combo or "").strip().lower()
        if not combo:
            return ""
        combo = combo.replace("control", "ctrl").replace("windows", "win")
        combo = combo.replace("command", "win").replace("cmd", "win")
        combo = combo.replace(" ", "")
        combo = combo.replace("++", "+")
        parts = [p for p in combo.split("+") if p]
        aliases = {
            "return": "enter",
            "escape": "esc",
            "plus": "plus",
            "minus": "minus",
            "pagedown": "page down",
            "pageup": "page up",
            "up arrow": "up",
            "down arrow": "down",
            "left arrow": "left",
            "right arrow": "right",
        }
        parts = [aliases.get(p, p) for p in parts]

        # Deduplicar manteniendo modificadores en orden conocido.
        mods = [m for m in ("ctrl", "alt", "shift", "win") if m in parts]
        keys = [p for p in parts if p not in cls.MODIFIERS]
        if not keys and mods:
            keys = []
        # Para la tecla principal dejamos el orden del usuario, sin duplicados.
        seen: set[str] = set()
        unique_keys: list[str] = []
        for key in keys:
            if key not in seen:
                unique_keys.append(key)
                seen.add(key)
        return "+".join(mods + unique_keys)

    @classmethod
    def validate_hotkey(cls, combo: str, i18n=None) -> tuple[bool, str]:
        manager = i18n or LocalizationManager(preference="es")
        combo = cls.normalize_hotkey(combo)
        if not combo:
            return False, manager.translate("hotkeys.validation.empty")
        if combo in cls.RESERVED_COMBOS:
            return False, manager.translate("hotkeys.validation.reserved", combo=combo)
        parts = combo.split("+")
        mods = [p for p in parts if p in cls.MODIFIERS]
        keys = [p for p in parts if p not in cls.MODIFIERS]
        if not keys:
            return False, manager.translate("hotkeys.validation.main_key")
        if len(keys) > 1:
            return False, manager.translate("hotkeys.validation.one_key")
        key = keys[0]
        if not mods:
            if re.fullmatch(r"[a-z0-9]", key):
                return False, manager.translate("hotkeys.validation.bare_key")
            if key in {"space", "enter", "tab", "backspace", "delete"}:
                return False, manager.translate("hotkeys.validation.invasive")
        return True, "OK"

    def combo_conflict(self, combo: str, *, ignore_action: str | None = None) -> tuple[str, str] | None:
        combo = self.normalize_hotkey(combo)
        for aid, existing in self.get_hotkeys().items():
            if aid == ignore_action:
                continue
            if existing == combo:
                label = self.action_label(aid)
                return aid, label
        return None

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    def set_hotkey(self, action_id: str, key_combination: str) -> None:
        result = self.assign_hotkey(action_id, key_combination)
        if not result["ok"]:
            raise ValueError(result["message"])

    def assign_hotkey(self, action_id: str, key_combination: str) -> dict[str, Any]:
        action_id = str(action_id or "").strip()
        combo = self.normalize_hotkey(key_combination)
        if not action_id:
            return {"ok": False, "message": self._t("hotkeys.assign.invalid_action")}
        ok, msg = self.validate_hotkey(combo, self.i18n)
        if not ok:
            self.last_warning = msg
            return {"ok": False, "message": msg}

        hotkeys = self.get_hotkeys()
        conflict = self.combo_conflict(combo, ignore_action=action_id)
        removed: tuple[str, str] | None = None
        if conflict:
            old_aid, old_label = conflict
            hotkeys.pop(old_aid, None)
            removed = (old_aid, old_label)

        hotkeys[action_id] = combo
        self.data["hotkeys"] = hotkeys
        self.save()
        self.apply_hooks()
        msg = self._t("hotkeys.assign.saved", combo=combo)
        if removed:
            msg += self._t("hotkeys.assign.replaced", action=removed[1])
        self.last_warning = None
        return {"ok": True, "message": msg, "replaced": removed}

    def clear_hotkey(self, action_id: str) -> None:
        hotkeys = self.get_hotkeys()
        hotkeys.pop(str(action_id), None)
        self.data["hotkeys"] = hotkeys
        self.save()
        self.apply_hooks()

    def remove_hotkey(self, action_id: str) -> None:
        self.clear_hotkey(action_id)

    def reset_defaults(self) -> None:
        self.data["enabled"] = True
        self.data["suppress"] = False
        self.data["trigger_on_release"] = True
        self.data["cooldown_ms"] = 280
        self.data["hotkeys"] = dict(self.DEFAULT_HOTKEYS)
        self.save()
        self.apply_hooks()

    # ------------------------------------------------------------------ #
    # Acciones disponibles
    # ------------------------------------------------------------------ #
    def list_actions(self) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []

        def add(aid: str, name: str, group: str, action: dict[str, Any] | None = None, icon: str = "KEYBOARD_ROUNDED") -> None:
            actions.append({"id": aid, "name": name, "group": group, "action": action or self._static_action_payload(aid), "icon": icon})

        general = self._t("hotkeys.group.general")
        target = self._t("hotkeys.group.target")
        brightness = self._t("hotkeys.group.brightness")
        whites = self._t("hotkeys.group.whites")
        colors_group = self._t("hotkeys.group.colors")
        add("toggle", self._t("hotkeys.action.toggle"), general, {"type": "toggle"}, "POWER_SETTINGS_NEW_ROUNDED")
        add("on", self._t("hotkeys.action.on"), general, {"type": "turn_on"}, "LIGHT_MODE_ROUNDED")
        add("off", self._t("hotkeys.action.off"), general, {"type": "turn_off"}, "POWER_OFF_ROUNDED")
        add("reset", self._t("hotkeys.action.reset"), general, {"type": "method", "method": "reset_light"}, "RESTART_ALT_ROUNDED")
        add("target_single", self._t("hotkeys.action.target_single"), target, {"type": "target_mode", "value": "single"}, "FILTER_1_ROUNDED")
        add("target_all", self._t("hotkeys.action.target_all"), target, {"type": "target_mode", "value": "all"}, "SELECT_ALL_ROUNDED")

        for aid, key, value in (
            ("bri_up", "hotkeys.action.bri_up", 10),
            ("bri_down", "hotkeys.action.bri_down", -10),
        ):
            add(aid, self._t(key), brightness, {"type": "brightness_delta", "value": value}, "BRIGHTNESS_6_ROUNDED")
        for pct in (10, 25, 50, 75, 100):
            add(f"bri_{pct}", self._t("hotkeys.action.brightness", value=pct), brightness, {"type": "brightness", "value": pct}, "BRIGHTNESS_6_ROUNDED")

        for aid, key, pct in (
            ("white_warm", "hotkeys.action.white_warm", 10),
            ("white_neutral", "hotkeys.action.white_neutral", 50),
            ("white_cold", "hotkeys.action.white_cold", 100),
        ):
            add(aid, self._t(key), whites, {"type": "white_percent", "value": pct}, "WB_SUNNY_ROUNDED")
        for pct in (0, 25, 50, 75, 100):
            add(f"white_{pct}", self._t("hotkeys.action.white_range", value=pct), whites, {"type": "white_percent", "value": pct}, "WB_SUNNY_ROUNDED")

        colors = {
            "red": "#ff0000",
            "green": "#00ff00",
            "blue": "#0000ff",
            "cyan": "#00ffff",
            "magenta": "#ff00ff",
            "orange": "#ff7f00",
            "pink": "#ff40a0",
            "yellow": "#ffd000",
        }
        for key, hx in colors.items():
            add(f"color_{key}", self._t(f"color.name.{key}"), colors_group, {"type": "rgb", "value": hx}, "PALETTE_ROUNDED")
        add("color_custom", self._t("hotkeys.action.color_custom"), colors_group, None, "COLOR_LENS_ROUNDED")

        # Colores personalizados ya guardados.
        for aid in self.get_hotkeys().keys():
            if isinstance(aid, str) and aid.startswith("color_hex_"):
                raw = aid.removeprefix("color_hex_")[:6]
                if re.fullmatch(r"[0-9a-fA-F]{6}", raw):
                    add(aid, self._t("hotkeys.action.color_hex", value=raw.upper()), self._t("hotkeys.group.custom_colors"), {"type": "rgb", "value": f"#{raw}"}, "COLOR_LENS_ROUNDED")

        try:
            from core import wiz_scenes
            for scene in wiz_scenes.CATALOG.values():
                add(f"scene_{scene.id}", translated_scene_name(self.i18n, scene.id, scene.name), self._t("hotkeys.group.wiz_scenes"), {"type": "scene", "value": {"sceneId": scene.id, "speed": 100}}, "AUTO_AWESOME_ROUNDED")
        except Exception:
            pass

        try:
            for fav in FavoritesManager().get_favorites():
                uid = fav.get("id")
                if uid:
                    add(f"fav_{uid}", translated_favorite_name(self.i18n, fav) or self._t("color_studio.favorite_default"), self._t("hotkeys.group.favorites"), {"type": "favorite", "value": uid}, "STAR_ROUNDED")
        except Exception:
            pass

        try:
            for scene in CustomScenesManager().get_scenes():
                uid = scene.get("id")
                if uid:
                    add(f"custom_{uid}", str(scene.get("name") or self._t("scenes.custom_fallback")), self._t("hotkeys.group.my_scenes"), {"type": "custom_scene", "value": uid}, "AUTO_FIX_HIGH_ROUNDED")
        except Exception:
            pass

        try:
            from config.routines_manager import RoutinesManager
            for routine in RoutinesManager(i18n=self.i18n).get_routines():
                uid = routine.get("id")
                if uid:
                    add(f"routine_{uid}", translated_default_routine_name(self.i18n, routine) or self._t("routines.fallback_name"), self._t("hotkeys.group.routines"), {"type": "routine", "value": uid}, "ROCKET_LAUNCH_ROUNDED")
        except Exception:
            pass

        return actions

    def action_by_id(self, action_id: str) -> dict[str, Any] | None:
        action_id = str(action_id or "")
        for action in self.list_actions():
            if action.get("id") == action_id:
                return action
        # Fallback para IDs dinámicos no listados todavía.
        payload = self._static_action_payload(action_id)
        if payload:
            return {"id": action_id, "name": self._fallback_label(action_id), "group": self._t("hotkeys.group.custom"), "action": payload}
        return None

    def action_label(self, action_id: str) -> str:
        action_id = str(action_id or "")
        for action in self.list_actions():
            if action.get("id") == action_id:
                return str(action.get("name") or action_id)
        return self._fallback_label(action_id)

    def _fallback_label(self, action_id: str) -> str:
        if str(action_id).startswith("color_hex_"):
            return self._t("hotkeys.action.color_hex", value=str(action_id).removeprefix("color_hex_")[:6].upper())
        if str(action_id).startswith("routine_"):
            return self._t("routines.fallback_name") + " " + str(action_id).split("_", 1)[1]
        return str(action_id)

    def _static_action_payload(self, action_id: str) -> dict[str, Any] | None:
        aid = str(action_id or "").strip()
        static: dict[str, dict[str, Any]] = {
            "toggle": {"type": "toggle"},
            "on": {"type": "turn_on"},
            "off": {"type": "turn_off"},
            "reset": {"type": "method", "method": "reset_light"},
            "target_single": {"type": "target_mode", "value": "single"},
            "target_all": {"type": "target_mode", "value": "all"},
            "bri_up": {"type": "brightness_delta", "value": 10},
            "bri_down": {"type": "brightness_delta", "value": -10},
            "white_warm": {"type": "white_percent", "value": 10},
            "white_neutral": {"type": "white_percent", "value": 50},
            "white_cold": {"type": "white_percent", "value": 100},
            "color_red": {"type": "rgb", "value": "#ff0000"},
            "color_green": {"type": "rgb", "value": "#00ff00"},
            "color_blue": {"type": "rgb", "value": "#0000ff"},
            "color_cyan": {"type": "rgb", "value": "#00ffff"},
            "color_magenta": {"type": "rgb", "value": "#ff00ff"},
            "color_orange": {"type": "rgb", "value": "#ff7f00"},
            "color_pink": {"type": "rgb", "value": "#ff40a0"},
            "color_yellow": {"type": "rgb", "value": "#ffd000"},
        }
        if aid in static:
            return dict(static[aid])
        if aid.startswith("bri_") and aid.removeprefix("bri_").isdigit():
            return {"type": "brightness", "value": int(aid.removeprefix("bri_"))}
        if aid.startswith("white_") and aid.removeprefix("white_").isdigit():
            return {"type": "white_percent", "value": int(aid.removeprefix("white_"))}
        if aid.startswith("color_hex_"):
            raw = aid.removeprefix("color_hex_")[:6]
            if re.fullmatch(r"[0-9a-fA-F]{6}", raw):
                return {"type": "rgb", "value": f"#{raw}"}
        if aid.startswith("scene_") and aid.split("_", 1)[1].isdigit():
            return {"type": "scene", "value": {"sceneId": int(aid.split("_", 1)[1]), "speed": 100}}
        if aid.startswith("fav_"):
            return {"type": "favorite", "value": aid.split("_", 1)[1]}
        if aid.startswith("custom_"):
            return {"type": "custom_scene", "value": aid.split("_", 1)[1]}
        if aid.startswith("routine_"):
            return {"type": "routine", "value": aid.split("_", 1)[1]}
        return None

    # ------------------------------------------------------------------ #
    # Hooks
    # ------------------------------------------------------------------ #
    def _clear_hooks(self) -> None:
        with self._hook_lock:
            try:
                self._native_backend.stop()
            except Exception:
                pass
            self.last_backend = "none"
            if _keyboard is None:
                self._handles.clear()
                return
            for handle in list(self._handles):
                try:
                    _keyboard.remove_hotkey(handle)
                except Exception:
                    pass
            self._handles.clear()

    def apply_hooks(self) -> None:
        """Registra hotkeys de forma atómica y conserva resultados parciales.

        En Windows se intenta ``RegisterHotKey`` primero. Si solo algunas
        combinaciones fallan, el fallback ``keyboard`` se aplica únicamente a
        esas combinaciones, evitando hooks duplicados para las que ya quedaron
        nativas.
        """
        with self._hook_lock:
            self._clear_hooks()
            self.last_error = None
            self.last_warning = None

            entries: list[dict[str, Any]] = []
            if self.is_enabled():
                for action_id, keys in self.get_hotkeys().items():
                    cb = self._create_callback(action_id)
                    if cb:
                        entries.append({"id": action_id, "combo": keys, "callback": cb})

            self._registration_report = {
                "backend": "none",
                "total": len(entries),
                "native": 0,
                "keyboard": 0,
                "failed": [],
            }
            if not self.is_enabled():
                return
            if not entries:
                self.last_warning = self._t("hotkeys.warning.none_configured")
                return

            preference = self.backend_preference()
            native_success: list[dict[str, Any]] = []
            native_failed: list[dict[str, Any]] = []

            if os.name == "nt" and preference in {"auto", "native"}:
                try:
                    self._native_backend.start(entries)
                    native_success = self._native_backend.successful_entries
                    native_failed = self._native_backend.failed_entries
                except Exception as exc:
                    native_failed = [
                        {**entry, "error": str(exc)}
                        for entry in entries
                    ]

                self._registration_report["native"] = len(native_success)

                if preference == "native":
                    self.last_backend = "windows" if native_success else "none"
                    self._registration_report["backend"] = self.last_backend
                    self._registration_report["failed"] = self._public_failures(native_failed)
                    if native_failed:
                        message = self._failure_message(native_failed)
                        if native_success:
                            self.last_warning = message
                        else:
                            self.last_error = message
                    return

                if native_success and not native_failed:
                    self.last_backend = "windows"
                    self._registration_report["backend"] = "windows"
                    return

                if native_success and native_failed:
                    keyboard_success: list[dict[str, Any]] = []
                    keyboard_failed: list[dict[str, Any]] = []
                    if _keyboard is not None:
                        keyboard_success, keyboard_failed = self._register_keyboard_entries(native_failed)
                    else:
                        keyboard_failed = native_failed

                    self._registration_report["keyboard"] = len(keyboard_success)
                    self._registration_report["failed"] = self._public_failures(keyboard_failed)
                    if keyboard_success:
                        self.last_backend = "hybrid"
                        self._registration_report["backend"] = "hybrid"
                        if keyboard_failed:
                            self.last_warning = self._failure_message(keyboard_failed)
                        else:
                            count = len(keyboard_success)
                            self.last_warning = self.i18n.translate_count(
                                "hotkeys.warning.hybrid_fallback",
                                count,
                            )
                    else:
                        self.last_backend = "windows"
                        self._registration_report["backend"] = "windows"
                        self.last_warning = self._failure_message(keyboard_failed)
                    return

            # Si Windows no registró ninguno, o se forzó keyboard, registramos
            # el conjunto completo mediante el fallback histórico.
            if _keyboard is None:
                detail = self._t("hotkeys.dependency.keyboard_missing", error=_IMPORT_ERROR)
                if native_failed:
                    detail = f"{self._failure_message(native_failed)} {detail}"
                self.last_error = detail
                self._registration_report["failed"] = self._public_failures(native_failed or entries)
                return

            keyboard_success, keyboard_failed = self._register_keyboard_entries(entries)
            self._registration_report["keyboard"] = len(keyboard_success)
            self._registration_report["failed"] = self._public_failures(keyboard_failed)
            if keyboard_success:
                self.last_backend = "keyboard"
                self._registration_report["backend"] = "keyboard"
                if keyboard_failed:
                    self.last_warning = self._failure_message(keyboard_failed)
                elif native_failed and preference == "auto":
                    self.last_warning = self._t("hotkeys.warning.keyboard_fallback")
            else:
                self.last_error = self._failure_message(keyboard_failed or native_failed)

    def _register_keyboard_entries(
        self,
        entries: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        successful: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        if _keyboard is None:
            return successful, [
                {**entry, "error": self._t("hotkeys.dependency.keyboard_missing", error=_IMPORT_ERROR)}
                for entry in entries
            ]

        suppress = self.suppress_enabled()
        release = self.trigger_on_release()
        for entry in entries:
            action_id = str(entry.get("id") or "")
            combo = str(entry.get("combo") or "")
            callback = entry.get("callback")
            try:
                handle = _keyboard.add_hotkey(
                    combo,
                    callback,
                    suppress=suppress,
                    trigger_on_release=release,
                )
                self._handles.append(handle)
                successful.append({"id": action_id, "combo": combo})
            except Exception as exc:
                failed.append({"id": action_id, "combo": combo, "error": str(exc)})
                _LOG.warning("No pude registrar hotkey %s=%s: %s", action_id, combo, exc)
        return successful, failed

    def _public_failures(self, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [
            {
                "id": str(row.get("id") or ""),
                "combo": str(row.get("combo") or ""),
                "error": self._friendly_hotkey_error(row, self.i18n),
            }
            for row in entries
        ]

    @staticmethod
    def _friendly_hotkey_error(row: dict[str, Any], i18n=None) -> str:
        manager = i18n or LocalizationManager(preference="es")
        error = str(row.get("error") or manager.translate("hotkeys.error.registration_default")).strip()
        code = row.get("error_code")
        lowered = error.lower()
        if code == 1409 or "already registered" in lowered or "ya se ha registrado" in lowered or "acceso rápido" in lowered:
            return manager.translate("hotkeys.error.already_used")
        if code == 5 or "access is denied" in lowered or "acceso denegado" in lowered:
            return manager.translate("hotkeys.error.windows_denied")
        if "no soportada" in lowered or "no soportado" in lowered:
            return manager.translate("hotkeys.error.native_unsupported")
        return error.rstrip(".;")

    def _failure_message(self, entries: list[dict[str, Any]]) -> str:
        if not entries:
            return self._t("hotkeys.error.registration_failed")
        visible = entries[:2]
        details = "; ".join(
            f"{str(row.get('combo') or 'hotkey')}: {self._friendly_hotkey_error(row, self.i18n)}"
            for row in visible
        )
        remaining = len(entries) - len(visible)
        if remaining > 0:
            details += "; " + self._t("hotkeys.error.more", count=remaining)
        return self.i18n.translate_count(
            "hotkeys.error.registration_detail",
            len(entries),
            details=details,
        )

    def _create_callback(self, action_id: str) -> Callable[[], None] | None:
        return lambda: self.execute_action(action_id)

    def read_hotkey_blocking(self) -> str | None:
        if _keyboard is None:
            self.last_error = self._t("hotkeys.error.recording_unavailable", error=_IMPORT_ERROR)
            return None
        # Mientras se graba, quitamos hooks propios para que la combinación no dispare acciones.
        was_enabled = self.is_enabled()
        self._clear_hooks()
        try:
            combo = _keyboard.read_hotkey(suppress=False)
            combo = self.normalize_hotkey(combo or "")
            if combo in {"esc", "escape"}:
                return None
            return combo
        except Exception as exc:
            self.last_error = str(exc)
            return None
        finally:
            if was_enabled:
                self.apply_hooks()

    # ------------------------------------------------------------------ #
    # Ejecución
    # ------------------------------------------------------------------ #
    def execute_action(self, action_id: str) -> None:
        action_id = str(action_id or "").strip()
        if not action_id:
            return
        now = time.monotonic()
        cooldown = self.cooldown_ms() / 1000.0
        with self._exec_lock:
            last = self._last_exec.get(action_id, 0.0)
            if now - last < cooldown:
                return
            self._last_exec[action_id] = now

        # Camino rápido: evita leer favoritos/rutinas JSON para acciones comunes
        # como toggle/brillo/color/escena/rutina por ID.
        payload = self._static_action_payload(action_id)
        if not isinstance(payload, dict):
            action = self.action_by_id(action_id)
            if not action:
                self.last_error = self._t("hotkeys.error.action_not_found", action_id=action_id)
                return
            payload = action.get("action")
        if not isinstance(payload, dict):
            self.last_error = self._t("hotkeys.error.action_no_payload", action_id=action_id)
            return
        try:
            executor = self._executor_instance()
            # Siempre en thread: el callback global no debe bloquearse.
            executor.execute(payload, threaded=True)
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            _LOG.debug("Hotkey action falló: %s", action_id, exc_info=True)

    def _executor_instance(self):
        if self._executor is None:
            from core.action_sequence import ActionSequenceExecutor

            self._executor = ActionSequenceExecutor(self.wiz)
        return self._executor

    def stop(self) -> None:
        self._clear_hooks()

    # ------------------------------------------------------------------ #
    # Utilidades backup/export
    # ------------------------------------------------------------------ #
    def configured_rows(self) -> list[dict[str, Any]]:
        rows = []
        for aid, combo in sorted(self.get_hotkeys().items()):
            action = self.action_by_id(aid) or {"id": aid, "name": self.action_label(aid), "group": self._t("hotkeys.group.custom")}
            rows.append({"id": aid, "combo": combo, "name": action.get("name", aid), "group": action.get("group", "")})
        return rows

    def export_json(self) -> str:
        payload = {
            "enabled": self.is_enabled(),
            "suppress": self.suppress_enabled(),
            "trigger_on_release": self.trigger_on_release(),
            "cooldown_ms": self.cooldown_ms(),
            "backend": self.backend_preference(),
            "hotkeys": self.get_hotkeys(),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)
