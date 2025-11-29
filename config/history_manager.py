import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

HISTORY_PATH = os.path.join(os.path.dirname(__file__), 'json', 'history.json')

class HistoryManager:
    """
    Gestor de historial de la app WiZ. Permite cargar, guardar y administrar historial de acciones.
    """
    def __init__(self) -> None:
        self.file_path: str = HISTORY_PATH
        ensure_json_file(self.file_path)
        self.history: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando historial: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando historial: {e}")

    def add_entry(self, entry: dict) -> None:
        """
        Agrega una entrada al historial.
        """
        key = entry.get('timestamp')
        if key:
            self.history[key] = entry
            self.save()
        else:
            logging.warning("Intento de agregar entrada sin timestamp.")

    def get_history(self) -> Dict[str, dict]:
        """
        Devuelve todo el historial registrado.
        """
        return self.history
