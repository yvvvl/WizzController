from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .paths import config_dir


def default_config_path() -> Path:
    return config_dir() / "config.json"


def ensure_json_file(file_path: str | os.PathLike[str], default_data: Any = None) -> None:
    if default_data is None:
        default_data = {}
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        with temporary.open("w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)


class ConfigManager:
    def __init__(self, filepath: str | os.PathLike[str] | None = None):
        self.file_path = str(Path(filepath).expanduser().resolve()) if filepath else str(default_config_path())
        self.config: dict[str, Any] = {}
        ensure_json_file(self.file_path, self._get_defaults())
        self._load()
        self._merge_defaults()

    def _load(self) -> None:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.config = loaded if isinstance(loaded, dict) else self._get_defaults()
        except Exception as exc:
            logging.error("Error cargando config: %s", exc)
            self.config = self._get_defaults()

    def _merge_defaults(self) -> None:
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

    def save(self) -> None:
        path = Path(self.file_path)
        temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, path)
        except Exception as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            logging.error("Error guardando config: %s", exc)

    def _get_defaults(self) -> dict[str, Any]:
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
        width = max(400, int(width))
        height = max(500, int(height))
        self.config["window"] = {
            "width": width,
            "height": height,
            "top": int(top) if top is not None else -1,
            "left": int(left) if left is not None else -1,
            "maximized": bool(maximized),
        }
        self.save()
