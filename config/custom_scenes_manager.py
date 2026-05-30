from __future__ import annotations

import time
import uuid
from typing import Any

from .base_manager import JsonManager


class CustomScenesManager(JsonManager):
    """Escenas creadas por el usuario.

    No son escenas internas grabadas en la ampolleta; son presets locales de la app:
    - rgb: {r,g,b,dimming?}
    - white: {temp,dimming?}
    - scene: {sceneId,speed?,dimming?}
    - combo: lista corta de acciones aplicadas en orden
    """

    def __init__(self):
        super().__init__("custom_scenes.json", default_data=[])
        if not isinstance(self.data, list):
            self.data = []
            self.save()

    def get_scenes(self) -> list[dict[str, Any]]:
        return self.data if isinstance(self.data, list) else []

    def get_scene(self, uid: str) -> dict[str, Any] | None:
        for scene in self.get_scenes():
            if scene.get("id") == uid:
                return scene
        return None

    def add_scene(self, name: str, mode: str, value: Any, icon: str = "AUTO_AWESOME") -> dict[str, Any]:
        now = time.time()
        scene = {
            "id": str(uuid.uuid4()),
            "name": str(name or "Mi escena").strip() or "Mi escena",
            "mode": str(mode or "rgb").strip(),
            "value": value,
            "icon": str(icon or "AUTO_AWESOME"),
            "created_at": now,
            "updated_at": now,
        }
        self.data.append(scene)
        self.save()
        return scene

    def update_scene(self, uid: str, name: str | None = None, mode: str | None = None, value: Any = None, icon: str | None = None) -> bool:
        scene = self.get_scene(uid)
        if not scene:
            return False
        if name is not None:
            scene["name"] = str(name).strip() or scene.get("name") or "Mi escena"
        if mode is not None:
            scene["mode"] = str(mode).strip() or scene.get("mode") or "rgb"
        if value is not None:
            scene["value"] = value
        if icon is not None:
            scene["icon"] = str(icon).strip() or "AUTO_AWESOME"
        scene["updated_at"] = time.time()
        self.save()
        return True

    def remove_scene(self, uid: str) -> bool:
        before = len(self.get_scenes())
        self.data = [s for s in self.get_scenes() if s.get("id") != uid]
        if len(self.data) != before:
            self.save()
            return True
        return False

    def scene_from_state(self, state: dict[str, Any], name: str = "Escena actual") -> dict[str, Any]:
        dimming = int(state.get("dimming", 100) or 100)
        if "sceneId" in state:
            return self.add_scene(name, "scene", {"sceneId": int(state.get("sceneId", 18)), "speed": int(state.get("speed", 100) or 100), "dimming": dimming}, "AUTO_AWESOME")
        if "temp" in state:
            return self.add_scene(name, "white", {"temp": int(state.get("temp", 4000)), "dimming": dimming}, "LIGHT_MODE")
        if all(k in state for k in ("r", "g", "b")):
            return self.add_scene(name, "rgb", {"r": int(state.get("r", 255)), "g": int(state.get("g", 255)), "b": int(state.get("b", 255)), "dimming": dimming}, "PALETTE")
        return self.add_scene(name, "white", {"temp": 4000, "dimming": dimming}, "LIGHT_MODE")
