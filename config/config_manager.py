import os
import json
import logging
from typing import Dict, Any

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'json', 'config.json')

def ensure_json_file(file_path: str, default_data: Any = None) -> None:
    if default_data is None:
        default_data = {}
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f)
    if os.path.getsize(file_path) == 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f)

class ConfigManager:
    """
    Gestor de configuración global de la app WiZ.
    """
    def __init__(self) -> None:
        self.file_path: str = CONFIG_PATH
        ensure_json_file(self.file_path)
        self.config: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def get(self, key: str) -> Any:
        return self.config.get(key)

# Example usage
if __name__ == "__main__":
    config = ConfigManager()
    config.set("last_brightness", 75)
    config.save_config()
    print(config.get("last_brightness"))