import os
import json
import logging
from typing import Any, Dict, List, Optional
from .config_manager import ensure_json_file

FAV_DIR = os.path.join(os.path.dirname(__file__), 'json')
FAV_PATH = os.path.join(FAV_DIR, 'favorites.json')

DEFAULT_FAVORITES = {
    "favorites": [
        {"label": "Encender", "action": "turn_on"},
        {"label": "50%", "action": "brightness_50"},
        {"label": "Cálida", "action": "temp_2700"},
        {"label": "Fiesta", "action": "scene_party"},
        {"label": "Navidad", "action": "scene_christmas"},
        {"label": "Apagar", "action": "turn_off"}
    ]
}

class FavoritesManager:
    def __init__(self) -> None:
        os.makedirs(FAV_DIR, exist_ok=True)
        ensure_json_file(FAV_PATH, DEFAULT_FAVORITES)
        self.file_path = FAV_PATH
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or 'favorites' not in data:
                    return DEFAULT_FAVORITES.copy()
                # Normalizar entradas
                favs = []
                for item in data.get('favorites', []):
                    if not isinstance(item, dict):
                        continue
                    favs.append({
                        'label': item.get('label', 'Favorito'),
                        'action': item.get('action', ''),
                        'param': item.get('param')
                    })
                return { 'favorites': favs }
        except Exception as e:
            logging.error(f"Error cargando favoritos: {e}")
            return DEFAULT_FAVORITES.copy()

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando favoritos: {e}")

    def get_favorites(self) -> List[Dict[str, Any]]:
        return list(self._data.get('favorites', []))

    def set_favorites(self, favorites: List[Dict[str, Any]]) -> None:
        self._data['favorites'] = favorites
        self.save()

    def add_favorite(self, label: str, action_id: str, param: Optional[Any] = None) -> None:
        favs = self._data.get('favorites', [])
        favs.append({'label': label, 'action': action_id, 'param': param})
        self._data['favorites'] = favs
        self.save()

    def remove_favorite(self, index: int) -> None:
        favs = self._data.get('favorites', [])
        if 0 <= index < len(favs):
            favs.pop(index)
            self._data['favorites'] = favs
            self.save()

    def move_favorite(self, index: int, direction: int) -> None:
        favs = self._data.get('favorites', [])
        new_index = index + direction
        if 0 <= index < len(favs) and 0 <= new_index < len(favs):
            favs[index], favs[new_index] = favs[new_index], favs[index]
            self._data['favorites'] = favs
            self.save()
