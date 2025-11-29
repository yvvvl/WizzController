import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

HOTKEYS_DIR = os.path.join(os.path.dirname(__file__), "json")
HOTKEYS_PATH = os.path.join(HOTKEYS_DIR, "hotkeys.json")

class HotkeysManager:
    def __init__(self) -> None:
        self.file_path: str = HOTKEYS_PATH
        ensure_json_file(self.file_path)
        self.hotkeys: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                normalized = {}
                for k, v in data.items():
                    if isinstance(v, str):
                        # Migración formato antiguo
                        normalized[k] = {"action": v, "enabled": True}
                    else:
                        # Asegurar que tenga campo enabled
                        if "enabled" not in v:
                            v["enabled"] = True
                        normalized[k] = v
                return normalized
        except Exception as e:
            logging.error(f"Error cargando hotkeys: {e}")
            return {}

    def save(self) -> None:
        try:
            os.makedirs(HOTKEYS_DIR, exist_ok=True)
            with open(HOTKEYS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.hotkeys, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando hotkeys: {e}")

    def set_hotkey(self, key_combo: str, action_id: str, color: list | None = None) -> None:
        if key_combo in self.hotkeys:
            del self.hotkeys[key_combo]
        
        entry = {"action": action_id, "enabled": True}
        if color:
            entry["color"] = color
        self.hotkeys[key_combo] = entry
        self.save()

    def set_enabled(self, key_combo: str, enabled: bool) -> None:
        """Activa o desactiva un atajo sin borrarlo."""
        if key_combo in self.hotkeys:
            self.hotkeys[key_combo]["enabled"] = enabled
            self.save()

    def remove_hotkey(self, key_combo: str) -> None:
        if key_combo in self.hotkeys:
            del self.hotkeys[key_combo]
            self.save()

    def get_hotkeys(self) -> Dict[str, Dict]:
        return self.hotkeys