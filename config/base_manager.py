from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any

from .paths import config_dir


class JsonManager:
    """Base thread-safe para persistencia JSON.

    En desarrollo conserva ``config/json``. En el ejecutable usa el storage
    persistente que Flet expone para la aplicación.
    """

    def __init__(
        self,
        filename: str,
        default_data: Any = None,
        *,
        directory: str | os.PathLike[str] | None = None,
    ) -> None:
        directory_path = Path(directory).expanduser().resolve() if directory else config_dir()
        directory_path.mkdir(parents=True, exist_ok=True)

        # Se mantienen atributos string por compatibilidad con managers/tests.
        self.base_dir = str(directory_path.parent)
        self.json_dir = str(directory_path)
        self.filepath = str(directory_path / filename)
        self.lock = threading.RLock()
        self.data = self._load_data(default_data)

    def _load_data(self, default_data: Any) -> Any:
        default = copy.deepcopy(default_data if default_data is not None else {})
        if not os.path.exists(self.filepath):
            return default
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default

    def save(self) -> None:
        """Escritura atómica para no dejar JSON truncados ante un cierre."""

        with self.lock:
            temporary = f"{self.filepath}.{os.getpid()}.tmp"
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                with open(temporary, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, self.filepath)
            except Exception as exc:
                try:
                    os.remove(temporary)
                except OSError:
                    pass
                print(f"Error guardando {self.filepath}: {exc}")

    def get(self, key: str, default: Any = None) -> Any:
        if isinstance(self.data, dict):
            return self.data.get(key, default)
        return default
