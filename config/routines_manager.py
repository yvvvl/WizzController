from __future__ import annotations

import copy
import uuid
from typing import Any

from .base_manager import JsonManager


DEFAULT_ROUTINES: list[dict[str, Any]] = [
    {
        "id": "study",
        "name": "Modo estudio",
        "description": "Blanco claro y brillo alto para trabajar.",
        "color": "#dfeeff",
        "icon": "SCHOOL_ROUNDED",
        "actions": [
            {"type": "turn_on"},
            {"type": "white_kelvin", "value": 5000},
            {"type": "brightness", "value": 80},
        ],
    },
    {
        "id": "night",
        "name": "Modo noche",
        "description": "Cálido y bajo brillo.",
        "color": "#ffb36b",
        "icon": "NIGHTLIGHT_ROUNDED",
        "actions": [
            {"type": "turn_on"},
            {"type": "white_kelvin", "value": 2200},
            {"type": "brightness", "value": 20},
        ],
    },
    {
        "id": "gaming",
        "name": "Modo juego",
        "description": "Azul/morado con brillo medio.",
        "color": "#7f00ff",
        "icon": "SPORTS_ESPORTS_ROUNDED",
        "actions": [
            {"type": "turn_on"},
            {"type": "rgb", "value": "#5500ff"},
            {"type": "brightness", "value": 45},
        ],
    },
    {
        "id": "cinema",
        "name": "Modo cine",
        "description": "Escena TV/Cine con brillo reducido.",
        "color": "#8b5cf6",
        "icon": "MOVIE_ROUNDED",
        "actions": [
            {"type": "turn_on"},
            {"type": "scene", "value": {"sceneId": 18, "speed": 100}},
            {"type": "brightness", "value": 35},
        ],
    },
    {
        "id": "reading",
        "name": "Modo lectura",
        "description": "Blanco neutro cómodo.",
        "color": "#ffe9d6",
        "icon": "MENU_BOOK_ROUNDED",
        "actions": [
            {"type": "turn_on"},
            {"type": "white_kelvin", "value": 4000},
            {"type": "brightness", "value": 70},
        ],
    },
    {
        "id": "soft_off",
        "name": "Apagado suave",
        "description": "Baja brillo un instante y apaga.",
        "color": "#5b6688",
        "icon": "POWER_SETTINGS_NEW_ROUNDED",
        "actions": [
            {"type": "brightness", "value": 10},
            {"type": "wait", "value": 250},
            {"type": "turn_off"},
        ],
    },
]


class RoutinesManager(JsonManager):
    """Gestor de rutinas/presets compuestos.

    No maneja horarios ni automatizaciones por tiempo. Solo guarda acciones
    reutilizables para UI y hotkeys.
    """

    def __init__(self) -> None:
        super().__init__("routines.json", default_data={"routines": copy.deepcopy(DEFAULT_ROUTINES)})
        if isinstance(self.data, list):
            self.data = {"routines": self.data}
        if not isinstance(self.data, dict):
            self.data = {"routines": copy.deepcopy(DEFAULT_ROUTINES)}
        if not isinstance(self.data.get("routines"), list):
            self.data["routines"] = copy.deepcopy(DEFAULT_ROUTINES)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        routines = self.data.get("routines", [])
        existing = {str(r.get("id")) for r in routines if isinstance(r, dict)}
        changed = False
        for routine in DEFAULT_ROUTINES:
            if routine["id"] not in existing:
                routines.append(copy.deepcopy(routine))
                changed = True
        self.data["routines"] = routines
        if changed:
            self.save()

    def get_routines(self) -> list[dict[str, Any]]:
        return [r for r in self.data.get("routines", []) if isinstance(r, dict)]

    def get_routine(self, uid: str) -> dict[str, Any] | None:
        uid = str(uid)
        for routine in self.get_routines():
            if str(routine.get("id")) == uid:
                return routine
        return None

    def add_routine(
        self,
        name: str,
        actions: list[dict[str, Any]],
        description: str = "",
        color: str = "#5b8cff",
        icon: str = "AUTO_AWESOME_ROUNDED",
    ) -> dict[str, Any]:
        routine = {
            "id": str(uuid.uuid4()),
            "name": (name or "Nueva rutina").strip(),
            "description": (description or "").strip(),
            "color": color or "#5b8cff",
            "icon": icon or "AUTO_AWESOME_ROUNDED",
            "actions": self.normalize_actions(actions),
        }
        self.data.setdefault("routines", []).append(routine)
        self.save()
        return routine

    def update_routine(self, uid: str, **fields) -> bool:
        routine = self.get_routine(uid)
        if not routine:
            return False
        for key in ("name", "description", "color", "icon"):
            if key in fields:
                routine[key] = fields[key]
        if "actions" in fields:
            routine["actions"] = self.normalize_actions(fields["actions"])
        self.save()
        return True

    def remove_routine(self, uid: str) -> bool:
        before = len(self.data.get("routines", []))
        self.data["routines"] = [r for r in self.get_routines() if str(r.get("id")) != str(uid)]
        if len(self.data["routines"]) != before:
            self.save()
            return True
        return False

    def duplicate_routine(self, uid: str) -> dict[str, Any] | None:
        routine = self.get_routine(uid)
        if not routine:
            return None
        new = copy.deepcopy(routine)
        new["id"] = str(uuid.uuid4())
        new["name"] = f"{new.get('name', 'Rutina')} copia"
        self.data.setdefault("routines", []).append(new)
        self.save()
        return new

    def normalize_actions(self, actions: Any) -> list[dict[str, Any]]:
        if not isinstance(actions, list):
            return []
        out: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            kind = str(action.get("type") or action.get("kind") or "").strip()
            if not kind:
                continue
            item: dict[str, Any] = {"type": kind}
            if "value" in action:
                item["value"] = action.get("value")
            for key in ("method", "ms", "speed", "name"):
                if key in action:
                    item[key] = action.get(key)
            out.append(item)
        return out

    def reset_defaults(self) -> None:
        self.data["routines"] = copy.deepcopy(DEFAULT_ROUTINES)
        self.save()
