from __future__ import annotations

import time
import uuid
from typing import Any

from .base_manager import JsonManager


class FavoritesManager(JsonManager):
    """CRUD simple para favoritos de luz.

    Estructura por item:
      id, name, type: rgb|white|scene|brightness, value, icon, created_at, updated_at
    """

    def __init__(self):
        super().__init__("favorites.json", default_data=[])
        if not isinstance(self.data, list):
            self.data = []
            self.save()

    def get_favorites(self) -> list[dict[str, Any]]:
        return self.data if isinstance(self.data, list) else []

    def get_favorite(self, uid: str) -> dict[str, Any] | None:
        for fav in self.get_favorites():
            if fav.get("id") == uid:
                return fav
        return None

    def add_favorite(self, name, ftype, value, icon="STAR") -> dict[str, Any]:
        now = time.time()
        fav = {
            "id": str(uuid.uuid4()),
            "name": str(name or "Favorito").strip() or "Favorito",
            "type": str(ftype or "rgb").strip(),
            "value": value,
            "icon": str(icon or "STAR"),
            "created_at": now,
            "updated_at": now,
        }
        self.data.append(fav)
        self.save()
        return fav

    def update_favorite(self, uid, name=None, ftype=None, value=None, icon=None) -> bool:
        fav = self.get_favorite(uid)
        if not fav:
            return False
        if name is not None:
            fav["name"] = str(name).strip() or fav.get("name") or "Favorito"
        if ftype is not None:
            fav["type"] = str(ftype).strip()
        if value is not None:
            fav["value"] = value
        if icon is not None:
            fav["icon"] = str(icon).strip() or "STAR"
        fav["updated_at"] = time.time()
        self.save()
        return True

    def remove_favorite(self, uid) -> bool:
        before = len(self.get_favorites())
        self.data = [f for f in self.get_favorites() if f.get("id") != uid]
        if len(self.data) != before:
            self.save()
            return True
        return False

    def seed_defaults(self) -> None:
        if self.get_favorites():
            return
        self.add_favorite("Rojo", "rgb", "#ff0000", "CIRCLE")
        self.add_favorite("Azul", "rgb", "#0066ff", "CIRCLE")
        self.add_favorite("Cálido", "white", 2700, "WB_TWILIGHT")
        self.add_favorite("Neutro", "white", 4000, "LIGHT_MODE")
        self.add_favorite("TV / Cine", "scene", {"sceneId": 18, "speed": 100}, "MOVIE")
