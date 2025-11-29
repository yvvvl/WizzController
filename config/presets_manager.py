import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

PRESETS_PATH = os.path.join(os.path.dirname(__file__), 'json', 'presets.json')

class PresetsManager:
    """
    Gestor de Colores Guardados (Presets).
    Estructura: {"Nombre": [r, g, b], ...}
    """
    def __init__(self) -> None:
        self.file_path: str = PRESETS_PATH
        ensure_json_file(self.file_path)
        self.presets: Dict[str, list] = self._load()

    def _load(self) -> Dict[str, list]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Si el archivo estaba vacío o era una lista antigua, reiniciamos a dict
                if isinstance(data, list): 
                    return {}
                return data
        except Exception as e:
            logging.error(f"Error cargando presets: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando presets: {e}")

    def add_preset(self, name: str, rgb: list) -> None:
        """Guarda un color RGB con un nombre."""
        if name and rgb:
            self.presets[name] = rgb
            self.save()

    def delete_preset(self, name: str) -> None:
        if name in self.presets:
            del self.presets[name]
            self.save()

    def get_presets(self) -> Dict[str, list]:
        return self.presets