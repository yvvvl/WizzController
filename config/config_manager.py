import os
import json
import logging
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "json", "config.json")


def ensure_json_file(file_path: str, default_data: Any = None) -> None:
    if default_data is None:
        default_data = {}
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)


class ConfigManager:
    def __init__(self, filepath=None):
        self.file_path = filepath if filepath else CONFIG_PATH
        self.config = {}
        ensure_json_file(self.file_path, self._get_defaults())
        self._load()
        self._merge_defaults()

    def _load(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error(f"Error cargando config: {e}")
            self.config = self._get_defaults()

    def _merge_defaults(self):
        defaults = self._get_defaults()
        changed = False
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
                changed = True
            elif isinstance(value, dict) and isinstance(self.config.get(key), dict):
                for subkey, subval in value.items():
                    if subkey not in self.config[key]:
                        self.config[key][subkey] = subval
                        changed = True
        if changed:
            self.save()

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando config: {e}")

    def _get_defaults(self):
        return {
            "window": {"width": 1080, "height": 720, "top": -1, "left": -1, "maximized": False},
            "control": {"mode": "single", "active_ip": None, "slider_interval_ms": 65},
        }

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def get_window_geometry(self):
        return self.config.get("window", self._get_defaults()["window"])

    def set_window_geometry(self, width, height, top, left, maximized):
        if width < 400:
            width = 400
        if height < 500:
            height = 500
        self.config["window"] = {
            "width": int(width),
            "height": int(height),
            "top": int(top) if top is not None else -1,
            "left": int(left) if left is not None else -1,
            "maximized": bool(maximized),
        }
        self.save()
