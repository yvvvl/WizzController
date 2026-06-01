from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


class AppRuntimeManager:
    """Configuración de arranque, voz automática y bandeja.

    No depende de Flet. Guarda todo en config/json/app_runtime.json.
    """

    DEFAULTS: dict[str, Any] = {
        "voice_start_mode": "manual",          # manual | always | remember
        "last_voice_continuous_active": False,
        "tray_enabled": True,
        "minimize_to_tray": True,
        "open_minimized": False,
        "startup_with_windows": False,
    }

    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.json_dir = self.base_dir / "json"
        self.path = self.json_dir / "app_runtime.json"
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
        self._sync_startup_flag()

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
        data.update(loaded)
        return data

    def _save_dict(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def save(self) -> None:
        self._save_dict(self.data)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def update(self, **kwargs: Any) -> None:
        self.data.update(kwargs)
        self.save()

    # ------------------------------------------------------------------ #
    # Voz automática
    # ------------------------------------------------------------------ #
    def should_start_voice(self) -> bool:
        mode = str(self.get("voice_start_mode", "manual"))
        if mode == "always":
            return True
        if mode == "remember":
            return bool(self.get("last_voice_continuous_active", False))
        return False

    def remember_voice_active(self, active: bool) -> None:
        self.set("last_voice_continuous_active", bool(active))

    # ------------------------------------------------------------------ #
    # Windows Startup
    # ------------------------------------------------------------------ #
    def _startup_command(self) -> str:
        # Repo root = padre de config/
        root = self.base_dir.parent
        main_py = root / "main.py"
        py = Path(sys.executable)
        pythonw = py.with_name("pythonw.exe") if os.name == "nt" else py
        exe = pythonw if pythonw.exists() else py
        return f'"{exe}" "{main_py}"'

    def _sync_startup_flag(self) -> None:
        # No escribimos registro aquí; solo normalizamos si no estamos en Windows.
        if os.name != "nt" and self.data.get("startup_with_windows"):
            self.data["startup_with_windows"] = False
            self.save()

    def set_startup_with_windows(self, enabled: bool) -> tuple[bool, str]:
        self.data["startup_with_windows"] = bool(enabled)
        self.save()
        if os.name != "nt":
            return False, "Inicio con Windows solo aplica en Windows."
        try:
            import winreg  # type: ignore
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, "WizZController", 0, winreg.REG_SZ, self._startup_command())
                else:
                    try:
                        winreg.DeleteValue(key, "WizZController")
                    except FileNotFoundError:
                        pass
            return True, "Inicio con Windows actualizado."
        except Exception as exc:
            return False, f"No se pudo modificar inicio con Windows: {exc}"
