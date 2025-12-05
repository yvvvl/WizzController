import json
import os
import logging
from typing import Dict, Any

class FavoritesManager:
    def __init__(self, filepath="config/json/favorites.json"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.filepath = os.path.join(base_dir, "config", "json", "favorites.json")
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            self._save({
                "rgb": {
                    "Rojo": {"r": 255, "g": 0, "b": 0},
                    "Azul": {"r": 0, "g": 0, "b": 255}
                },
                "white": {
                    "Cálido": {"temp": 2700},
                    "Frío": {"temp": 6500}
                },
                "scenes": {} # Nueva sección para escenas
            })

    def _load(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.filepath) or os.path.getsize(self.filepath) == 0:
                return {"rgb": {}, "white": {}, "scenes": {}}

            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)

            if isinstance(content, list):
                # Recuperación de emergencia
                return {"rgb": {}, "white": {}, "scenes": {}}

            # Asegurar claves
            if "rgb" not in content: content["rgb"] = {}
            if "white" not in content: content["white"] = {}
            if "scenes" not in content: content["scenes"] = {}
            
            return content

        except Exception:
            return {"rgb": {}, "white": {}, "scenes": {}}

    def _save(self, data):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando favoritos: {e}")

    # --- GETTERS ---
    def get_rgb_favorites(self): return self._load().get("rgb", {})
    def get_white_favorites(self): return self._load().get("white", {})
    def get_scene_favorites(self): return self._load().get("scenes", {})

    # --- ADDERS ---
    def add_rgb_favorite(self, name, r, g, b):
        data = self._load()
        data["rgb"][name] = {"r": int(r), "g": int(g), "b": int(b)}
        self._save(data)

    def add_white_favorite(self, name, kelvin):
        data = self._load()
        data["white"][name] = {"temp": int(kelvin)}
        self._save(data)

    def add_scene_favorite(self, name, scene_id):
        data = self._load()
        data["scenes"][name] = {"sceneId": int(scene_id)}
        self._save(data)

    # --- REMOVERS ---
    def remove_rgb_favorite(self, name):
        data = self._load()
        if name in data["rgb"]: del data["rgb"][name]; self._save(data)

    def remove_white_favorite(self, name):
        data = self._load()
        if name in data["white"]: del data["white"][name]; self._save(data)

    def remove_scene_favorite(self, name):
        data = self._load()
        if name in data["scenes"]: del data["scenes"][name]; self._save(data)