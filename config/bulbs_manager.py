import os
import json
import logging
from typing import Dict
from .config_manager import ensure_json_file

BULBS_PATH = os.path.join(os.path.dirname(__file__), 'json', 'bulbs.json')

class BulbsManager:
    """
    Gestor de bombillas WiZ. Permite cargar, guardar y administrar bombillas.
    """
    def __init__(self) -> None:
        self.file_path: str = BULBS_PATH
        ensure_json_file(self.file_path)
        self.bulbs: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando bombillas: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.bulbs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando bombillas: {e}")

    def add_bulb(self, bulb: dict) -> None:
        """
        Agrega una bombilla al registro.
        """
        ip = bulb.get('ip')
        if ip:
            self.bulbs[ip] = bulb
            self.save()
        else:
            logging.warning("Intento de agregar bombilla sin IP.")

    def get_bulbs(self) -> Dict[str, dict]:
        """
        Devuelve todas las bombillas registradas.
        """
        return self.bulbs

# Example usage
if __name__ == "__main__":
    manager = BulbsManager()
    manager.add_bulb({"id": "1", "ip": "192.168.1.100", "name": "Living Room"})
    print(manager.get_bulbs())