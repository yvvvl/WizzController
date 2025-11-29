import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

PRESETS_PATH = os.path.join(os.path.dirname(__file__), 'json', 'presets.json')

class PresetsManager:
    """
    Gestor de presets de la app WiZ. Permite cargar, guardar y administrar presets.
    """
    def __init__(self) -> None:
        self.file_path: str = PRESETS_PATH
        ensure_json_file(self.file_path)
        self.presets: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando presets: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando presets: {e}")

    def add_preset(self, preset: dict) -> None:
        """
        Agrega un preset al registro.
        """
        name = preset.get('name')
        if name:
            self.presets[name] = preset
            self.save()
        else:
            logging.warning("Intento de agregar preset sin nombre.")

    def get_presets(self) -> Dict[str, dict]:
        """
        Devuelve todos los presets registrados.
        """
        return self.presets
