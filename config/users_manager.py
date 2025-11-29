import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

USERS_PATH = os.path.join(os.path.dirname(__file__), 'json', 'users.json')

class UsersManager:
    """
    Gestor de usuarios de la app WiZ. Permite cargar, guardar y administrar usuarios.
    """
    def __init__(self) -> None:
        self.file_path: str = USERS_PATH
        ensure_json_file(self.file_path)
        self.users: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando usuarios: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando usuarios: {e}")

    def add_user(self, user: dict) -> None:
        """
        Agrega un usuario al registro.
        """
        key = user.get('username')
        if key:
            self.users[key] = user
            self.save()
        else:
            logging.warning("Intento de agregar usuario sin username.")

    def get_users(self) -> Dict[str, dict]:
        """
        Devuelve todos los usuarios registrados.
        """
        return self.users