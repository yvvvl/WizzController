from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Iterable

from app_meta import APP_REGISTRY_NAME
from config.paths import config_dir, project_root


class AppRuntimeManager:
    """Configuración de arranque, bandeja e inicio con Windows.

    En desarrollo guarda en ``config/json``. En un build Flet usa el storage
    persistente de la aplicación y resuelve el launcher real para el registro
    de inicio de Windows.
    """

    DEFAULTS: dict[str, Any] = {
        "tray_enabled": True,
        "minimize_to_tray": True,
        "open_minimized": False,
        "startup_with_windows": False,
    }

    def __init__(self) -> None:
        self.base_dir = config_dir()
        self.json_dir = self.base_dir
        self.path = self.json_dir / "app_runtime.json"
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.data = self._load()
        self._sync_startup_registration()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            self._save_dict(dict(self.DEFAULTS))
            return dict(self.DEFAULTS)
        try:
            with self.path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                loaded = {}
        except Exception:
            loaded = {}
        data = dict(self.DEFAULTS)
        for key in self.DEFAULTS:
            if key in loaded:
                data[key] = loaded[key]
        if data != loaded:
            self._save_dict(data)
        return data

    def _save_dict(self, data: dict[str, Any]) -> None:
        temporary = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with temporary.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.path)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def save(self) -> None:
        with self._lock:
            self._save_dict(self.data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self.data[key] = value
            self._save_dict(self.data)

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            self.data.update(kwargs)
            self._save_dict(self.data)

    # ------------------------------------------------------------------ #
    # Windows Startup
    # ------------------------------------------------------------------ #
    def _startup_command(self) -> str:
        packaged = resolve_packaged_executable()
        if packaged is not None:
            return subprocess.list2cmdline([str(packaged)])

        main_py = project_root() / "main.py"
        py = Path(sys.executable)
        pythonw = py.with_name("pythonw.exe") if os.name == "nt" else py
        executable = pythonw if pythonw.exists() else py
        return subprocess.list2cmdline([str(executable), str(main_py)])

    def _sync_startup_registration(self) -> None:
        """Mantiene coherente el JSON y el valor ``Run`` de Windows.

        Si el usuario ya activó el arranque automático y mueve/actualiza la
        build, se reescribe la ruta con el launcher actual. En otros sistemas
        la preferencia se normaliza a ``False``.
        """

        if os.name != "nt":
            if self.data.get("startup_with_windows"):
                self.data["startup_with_windows"] = False
                self._save_dict(self.data)
            return

        if not bool(self.data.get("startup_with_windows")):
            return

        try:
            current = _read_startup_value()
            desired = self._startup_command()
            if _normalize_command(current) != _normalize_command(desired):
                _write_startup_value(desired)
        except Exception as exc:
            # No desactivamos la preferencia por un fallo temporal de registro.
            logging.warning("[Startup] No se pudo sincronizar inicio con Windows: %s", exc)

    def set_startup_with_windows(self, enabled: bool) -> tuple[bool, str]:
        if os.name != "nt":
            with self._lock:
                self.data["startup_with_windows"] = False
                self._save_dict(self.data)
            return False, "Inicio con Windows solo aplica en Windows."

        try:
            if enabled:
                _write_startup_value(self._startup_command())
            else:
                _delete_startup_value()
        except Exception as exc:
            return False, f"No se pudo modificar inicio con Windows: {exc}"

        with self._lock:
            self.data["startup_with_windows"] = bool(enabled)
            self._save_dict(self.data)
        return True, "Inicio con Windows actualizado."


def _registry_key_path() -> str:
    return r"Software\Microsoft\Windows\CurrentVersion\Run"


def _read_startup_value() -> str | None:
    import winreg  # type: ignore

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _registry_key_path(),
            0,
            winreg.KEY_QUERY_VALUE,
        ) as key:
            value, _kind = winreg.QueryValueEx(key, APP_REGISTRY_NAME)
            return str(value or "")
    except FileNotFoundError:
        return None


def _write_startup_value(command: str) -> None:
    import winreg  # type: ignore

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        _registry_key_path(),
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(
            key,
            APP_REGISTRY_NAME,
            0,
            winreg.REG_SZ,
            str(command),
        )


def _delete_startup_value() -> None:
    import winreg  # type: ignore

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        _registry_key_path(),
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        try:
            winreg.DeleteValue(key, APP_REGISTRY_NAME)
        except FileNotFoundError:
            pass


def _normalize_command(command: str | None) -> str:
    return " ".join(str(command or "").strip().split()).casefold()


def resolve_packaged_executable() -> Path | None:
    """Resuelve el launcher de producción, no el Python embebido.

    ``flet build`` puede ejecutar el código Python dentro del proceso principal
    o en un hijo. Se inspecciona el módulo actual, ``sys.executable`` y la cadena
    de padres; se prioriza un ejecutable cuyo nombre contenga ``wizz``.
    """

    explicit = str(os.environ.get("WIZZ_EXECUTABLE") or "").strip()
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        return candidate if candidate.suffix.lower() == ".exe" else None

    packaged = bool(os.environ.get("FLET_APP_STORAGE_DATA")) or bool(
        getattr(sys, "frozen", False)
    )
    if os.name != "nt" or not packaged:
        return None

    candidates: list[Path] = []
    module_path = _current_module_executable()
    if module_path is not None:
        candidates.append(module_path)
    candidates.append(Path(sys.executable))
    candidates.extend(_process_tree_executables())

    ranked: list[tuple[int, int, Path]] = []
    for index, candidate in enumerate(_unique_paths(candidates)):
        try:
            path = candidate.expanduser().resolve()
        except Exception:
            continue
        if path.suffix.lower() != ".exe":
            continue
        stem = path.stem.casefold()
        if stem in {
            "python",
            "pythonw",
            "dart",
            "cmd",
            "powershell",
            "pwsh",
            "conhost",
            "explorer",
        }:
            continue
        score = 0
        if "wizz" in stem:
            score += 100
        if "flet" not in stem and "flutter" not in stem:
            score += 20
        if path.exists():
            score += 10
        ranked.append((score, -index, path))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    best = ranked[0]
    return best[2] if best[0] >= 20 else None


def _current_module_executable() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetModuleFileNameW(None, buffer, len(buffer))
        if length:
            return Path(buffer.value)
    except Exception:
        pass
    return None


def _process_tree_executables() -> list[Path]:
    try:
        import psutil  # type: ignore

        process = psutil.Process(os.getpid())
        rows = [process, *process.parents()[:4]]
        result: list[Path] = []
        for row in rows:
            try:
                result.append(Path(row.exe()))
            except Exception:
                continue
        return result
    except Exception:
        return []


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(os.path.abspath(str(path)))
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result
