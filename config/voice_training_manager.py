from __future__ import annotations

import time
import uuid
from typing import Any

from .base_manager import JsonManager


class VoiceTrainingManager(JsonManager):
    """Frases personalizadas para comandos de voz.

    Cada entrada guarda:
      id, phrase, action, notes, hit_count, created_at, updated_at
    donde action es un dict estable generado por el registry de acciones.
    """

    def __init__(self) -> None:
        super().__init__("voice_training.json", default_data=[])
        if not isinstance(self.data, list):
            self.data = []
            self.save()

    def get_entries(self) -> list[dict[str, Any]]:
        return self.data if isinstance(self.data, list) else []

    def add_entry(self, phrase: str, action: dict[str, Any], notes: str = "") -> dict[str, Any]:
        phrase = str(phrase or "").strip()
        if not phrase:
            raise ValueError("La frase no puede estar vacía")
        now = time.time()
        item = {
            "id": str(uuid.uuid4()),
            "phrase": phrase,
            "action": dict(action or {}),
            "notes": str(notes or ""),
            "hit_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        self.data.append(item)
        self.save()
        return item

    def remove_entry(self, uid: str) -> bool:
        before = len(self.get_entries())
        self.data = [x for x in self.get_entries() if x.get("id") != uid]
        if len(self.data) != before:
            self.save()
            return True
        return False

    def mark_used(self, uid: str) -> None:
        for item in self.get_entries():
            if item.get("id") == uid:
                item["hit_count"] = int(item.get("hit_count", 0) or 0) + 1
                item["updated_at"] = time.time()
                self.save()
                return
