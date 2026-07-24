from __future__ import annotations

import time
import uuid
from typing import Any

from .base_manager import JsonManager


_BUILTIN_LOCALIZED_NAMES = {
    "red": {"Rojo", "Red"},
    "blue": {"Azul", "Blue"},
    "warm": {"Cálido", "Warm"},
    "neutral": {"Neutro", "Neutral"},
    "cinema": {"TV / Cine", "TV / Cinema"},
}


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
        self._migrate_legacy_defaults()

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
            new_name = str(name).strip()
            builtin = str(fav.get("builtin") or "")
            if not builtin or new_name not in _BUILTIN_LOCALIZED_NAMES.get(builtin, set()):
                fav["name"] = new_name or fav.get("name") or "Favorito"
                fav.pop("builtin", None)
        if ftype is not None:
            if str(ftype).strip() != str(fav.get("type") or ""):
                fav.pop("builtin", None)
            fav["type"] = str(ftype).strip()
        if value is not None:
            if value != fav.get("value"):
                fav.pop("builtin", None)
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
        defaults = (
            ("red", "Rojo", "rgb", "#ff0000", "CIRCLE"),
            ("blue", "Azul", "rgb", "#0066ff", "CIRCLE"),
            ("warm", "Cálido", "white", 2700, "WB_TWILIGHT"),
            ("neutral", "Neutro", "white", 4000, "LIGHT_MODE"),
            ("cinema", "TV / Cine", "scene", {"sceneId": 18, "speed": 100}, "MOVIE"),
        )
        for builtin, name, kind, value, icon in defaults:
            self.add_favorite(name, kind, value, icon)["builtin"] = builtin
        self.save()

    @staticmethod
    def _legacy_builtin_key(favorite: dict[str, Any]) -> str | None:
        name = str(favorite.get("name") or "")
        kind = str(favorite.get("type") or "")
        value = favorite.get("value")
        if kind == "rgb" and str(value).casefold() == "#ff0000" and name == "Rojo":
            return "red"
        if kind == "rgb" and str(value).casefold() == "#0066ff" and name == "Azul":
            return "blue"
        if kind == "white" and str(value) == "2700" and name == "Cálido":
            return "warm"
        if kind == "white" and str(value) == "4000" and name == "Neutro":
            return "neutral"
        if kind == "scene" and isinstance(value, dict) and str(value.get("sceneId") or "") == "18" and name == "TV / Cine":
            return "cinema"
        return None

    def _migrate_legacy_defaults(self) -> None:
        candidates = [
            (favorite, self._legacy_builtin_key(favorite))
            for favorite in self.get_favorites()
            if not favorite.get("builtin")
        ]
        recognized = {key for _favorite, key in candidates if key}
        if len(recognized) < 4:
            return
        changed = False
        for favorite, key in candidates:
            if key:
                favorite["builtin"] = key
                changed = True
        if changed:
            self.save()
