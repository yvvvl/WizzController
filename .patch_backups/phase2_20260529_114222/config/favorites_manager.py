from __future__ import annotations

import uuid
from typing import Any

from .base_manager import JsonManager


class FavoritesManager(JsonManager):
    """CRUD simple de favoritos: rgb, white, scene."""

    def __init__(self):
        super().__init__("favorites.json", default_data=[])
        if not isinstance(self.data, list):
            self.data = []
            self.save()

    def get_favorites(self) -> list[dict[str, Any]]:
        return self.data if isinstance(self.data, list) else []

    def get_favorite(self, uid: str) -> dict[str, Any] | None:
        for fav in self.get_favorites():
            if str(fav.get("id")) == str(uid):
                return fav
        return None

    def add_favorite(self, name: str, ftype: str, value: Any, icon: str = "STAR") -> dict[str, Any]:
        fav = {
            "id": str(uuid.uuid4()),
            "name": (name or "Favorito").strip(),
            "type": self._clean_type(ftype),
            "value": self._clean_value(ftype, value),
            "icon": icon or self._default_icon(ftype),
        }
        self.data.append(fav)
        self.save()
        return fav

    def update_favorite(self, uid: str, name: str, ftype: str, value: Any, icon: str = "STAR") -> bool:
        fav = self.get_favorite(uid)
        if not fav:
            return False
        fav.update(
            {
                "name": (name or fav.get("name") or "Favorito").strip(),
                "type": self._clean_type(ftype),
                "value": self._clean_value(ftype, value),
                "icon": icon or self._default_icon(ftype),
            }
        )
        self.save()
        return True

    def remove_favorite(self, uid: str) -> bool:
        before = len(self.data)
        self.data = [f for f in self.get_favorites() if str(f.get("id")) != str(uid)]
        changed = len(self.data) != before
        if changed:
            self.save()
        return changed

    def _clean_type(self, ftype: str) -> str:
        ftype = str(ftype or "rgb").lower()
        return ftype if ftype in ("rgb", "white", "scene") else "rgb"

    def _clean_value(self, ftype: str, value: Any) -> Any:
        ftype = self._clean_type(ftype)
        if ftype == "rgb":
            h = str(value or "#ffffff").strip()
            if not h.startswith("#"):
                h = "#" + h
            return h[:7].lower()
        if ftype in ("white", "scene"):
            try:
                return int(value)
            except Exception:
                return 4000 if ftype == "white" else 18
        return value

    def _default_icon(self, ftype: str) -> str:
        return {"rgb": "PALETTE", "white": "LIGHT_MODE", "scene": "AUTO_AWESOME"}.get(str(ftype), "STAR")
