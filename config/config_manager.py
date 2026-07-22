from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .paths import config_dir


_CONFIG_IO_LOCK = threading.RLock()
_REPLACE_RETRIES = 8
_RETRYABLE_WINERRORS = {5, 32}


def default_config_path() -> Path:
    return config_dir() / "config.json"


def _is_retryable_replace_error(exc: OSError) -> bool:
    return (
        isinstance(exc, PermissionError)
        or getattr(exc, "winerror", None) in _RETRYABLE_WINERRORS
    )


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(
        f"{path.name}.{os.getpid()}.{threading.get_ident()}."
        f"{uuid.uuid4().hex}.tmp"
    )

    last_error: OSError | None = None

    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=4, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())

        for attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(temporary, path)
                return
            except OSError as exc:
                if not _is_retryable_replace_error(exc):
                    raise

                last_error = exc

                if attempt + 1 < _REPLACE_RETRIES:
                    time.sleep(0.025 * (attempt + 1))

        if last_error is not None:
            raise last_error

        raise OSError(f"No se pudo reemplazar {path}")

    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def ensure_json_file(
    file_path: str | os.PathLike[str],
    default_data: Any = None,
) -> None:
    if default_data is None:
        default_data = {}

    path = Path(file_path)

    with _CONFIG_IO_LOCK:
        if not path.exists() or path.stat().st_size == 0:
            _atomic_write_json(path, default_data)


class ConfigManager:
    def __init__(
        self,
        filepath: str | os.PathLike[str] | None = None,
    ):
        self.file_path = (
            str(Path(filepath).expanduser().resolve())
            if filepath
            else str(default_config_path())
        )
        self.config: dict[str, Any] = {}

        ensure_json_file(self.file_path, self._get_defaults())
        self._load()
        self._merge_defaults()

    def _load(self) -> None:
        try:
            with open(self.file_path, "r", encoding="utf-8") as stream:
                loaded = json.load(stream)

            self.config = (
                loaded
                if isinstance(loaded, dict)
                else self._get_defaults()
            )
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
            elif (
                isinstance(value, dict)
                and isinstance(self.config.get(key), dict)
            ):
                for subkey, subvalue in value.items():
                    if subkey not in self.config[key]:
                        self.config[key][subkey] = subvalue
                        changed = True

        if changed:
            self.save()

    def _read_current(self) -> dict[str, Any]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as stream:
                loaded = json.load(stream)

            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}

    def _save_unlocked(self) -> None:
        path = Path(self.file_path)

        try:
            _atomic_write_json(path, self.config)
        except Exception as exc:
            logging.error("Error guardando config: %s", exc)

    def save(self) -> None:
        with _CONFIG_IO_LOCK:
            self._save_unlocked()

    def _get_defaults(self) -> dict[str, Any]:
        return {
            "window": {
                "width": 1080,
                "height": 720,
                "top": -1,
                "left": -1,
                "maximized": False,
            },
            "control": {
                "mode": "single",
                "active_ip": None,
                "slider_interval_ms": 65,
            },
            "removed_bulbs": [],
        }

    def set(self, key: str, value: Any) -> None:
        with _CONFIG_IO_LOCK:
            latest = self._read_current()

            if latest:
                self.config = latest

            self.config[key] = value
            self._save_unlocked()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def get_window_geometry(self):
        return self.config.get(
            "window",
            self._get_defaults()["window"],
        )

    def set_window_geometry(
        self,
        width,
        height,
        top,
        left,
        maximized,
    ):
        width = max(400, int(width))
        height = max(500, int(height))

        self.set(
            "window",
            {
                "width": width,
                "height": height,
                "top": int(top) if top is not None else -1,
                "left": int(left) if left is not None else -1,
                "maximized": bool(maximized),
            },
        )
