import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

SCENES_PATH = os.path.join(os.path.dirname(__file__), 'json', 'scenes.json')

class ScenesManager:
    """
    Gestor de escenas de la app WiZ. Permite cargar, guardar y administrar escenas.
    """
    def __init__(self) -> None:
        self.file_path: str = SCENES_PATH
        ensure_json_file(self.file_path)
        self.scenes: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando escenas: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.scenes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando escenas: {e}")

    def add_scene(self, scene: dict) -> None:
        """
        Agrega una escena al registro.
        """
        name = scene.get('name')
        if name:
            self.scenes[name] = scene
            self.save()
        else:
            logging.warning("Intento de agregar escena sin nombre.")

    def get_scenes(self) -> Dict[str, dict]:
        """
        Devuelve todas las escenas registradas.
        """
        return self.scenes
