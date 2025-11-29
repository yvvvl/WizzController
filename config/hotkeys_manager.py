import os
import json
import logging
from typing import Optional, Dict
from .config_manager import ensure_json_file

HOTKEYS_DIR = os.path.join(os.path.dirname(__file__), "json")
HOTKEYS_PATH = os.path.join(HOTKEYS_DIR, "hotkeys.json")

class HotkeysManager:
    """
    Gestor de hotkeys para la aplicación WiZ. Permite cargar, guardar, asignar y eliminar atajos de teclado.
    """
    def __init__(self) -> None:
        self.file_path: str = HOTKEYS_PATH
        ensure_json_file(self.file_path)
        self.hotkeys: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
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
        """
        Asigna una hotkey única a una acción. Si ya existe otra combinación para la acción, la elimina.
        """
        for k, v in list(self.hotkeys.items()):
            if isinstance(v, dict) and v.get("action") == action_id:
                del self.hotkeys[k]
        if color:
            self.hotkeys[key_combo] = {"action": action_id, "color": color}
        else:
            self.hotkeys[key_combo] = {"action": action_id}
        self.save()

    def remove_hotkey(self, key_combo: str) -> None:
        """
        Elimina una hotkey por combinación de teclas.
        """
        if key_combo in self.hotkeys:
            del self.hotkeys[key_combo]
            self.save()

    def get_action(self, key_combo: str) -> str | None:
        """
        Devuelve el id de acción asociado a una hotkey.
        """
        entry = self.hotkeys.get(key_combo)
        if isinstance(entry, dict):
            return entry.get("action")
        return None

    def get_hotkeys(self) -> Dict[str, Dict]:
        """
        Devuelve todas las hotkeys registradas.
        """
        return self.hotkeys
