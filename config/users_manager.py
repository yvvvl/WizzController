import logging
from .base_manager import JsonManager

class UsersManager(JsonManager):
    def __init__(self):
        super().__init__("users.json")

    def add_user(self, user: dict) -> None:
        key = user.get('username')
        if key:
            self.data[key] = user
            self.save()
        else:
            logging.warning("Intento de agregar usuario sin username.")

    def get_users(self) -> dict:
        return self.data
