"""Rutas persistentes y assets para desarrollo y builds de Flet.

Soporte multiplataforma (Linux, Windows, macOS).
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
from pathlib import Path

from app_meta import APP_ARTIFACT

_INIT_LOCK = threading.Lock()
_INITIALIZED_DIRS: set[Path] = set()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def assets_dir() -> Path:
    configured = str(os.environ.get("FLET_ASSETS_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (project_root() / "assets").resolve()


def is_flet_build() -> bool:
    executable_name = Path(sys.executable).name.lower()
    executable_dir = Path(sys.executable).resolve().parent
    packaged_marker = executable_dir / f"{APP_ARTIFACT}.exe"
    argv_name = Path(str(sys.argv[0] or "")).name.lower()
    # Flet's Windows launcher can execute Python from the bundled app.zip
    # rather than from WizZDesktop.exe itself.  In that mode neither
    # ``sys.frozen`` nor the executable name is a reliable marker.
    module_path = str(Path(__file__).resolve()).lower()
    embedded_runtime = (
        ".zip" in module_path
        or "flutter_assets" in module_path
        or Path(__file__).suffix.lower() == ".pyc"
    )
    return bool(
        str(os.environ.get("FLET_APP_STORAGE_DATA") or "").strip()
        or getattr(sys, "frozen", False)
        or executable_name == f"{APP_ARTIFACT.lower()}.exe"
        or packaged_marker.is_file()
        or argv_name == f"{APP_ARTIFACT.lower()}.exe"
        or embedded_runtime
    )


def config_dir() -> Path:
    """Directorio writable para los JSON reales de la aplicación."""

    # 1. Override explícito por variable de entorno (para tests o portable)
    override = str(os.environ.get("WIZZ_CONFIG_DIR") or "").strip()
    if override:
        target = Path(override).expanduser().resolve()
        return _prepare(target, migrate=False)

    flet_storage = str(os.environ.get("FLET_APP_STORAGE_DATA") or "").strip()

    # 2. Si es una build empaquetada (AppImage / PyInstaller / Flet Build)
    if is_flet_build():
        if flet_storage:
            target = Path(flet_storage).expanduser().resolve() / "config"
            return _prepare(target, migrate=True)

        # Estándar Linux XDG si no hay ruta Flet explícita
        if sys.platform.startswith("linux"):
            xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
            target = Path(xdg_config) / APP_ARTIFACT / "config"
            return _prepare(target, migrate=True)

        # Windows packaged builds must keep user data outside the install
        # directory so upgrades do not overwrite configuration.
        if sys.platform.startswith("win"):
            local_app_data = os.environ.get(
                "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
            )
            target = Path(local_app_data) / APP_ARTIFACT / "config"
            return _prepare(target, migrate=True)

    # 3. Modo Desarrollo Local (Guarda en el propio repo config/json)
    target = project_root() / "config" / "json"
    return _prepare(target, migrate=False)


def logs_dir() -> Path:
    """Directorio para los logs de la aplicación."""
    flet_storage = str(os.environ.get("FLET_APP_STORAGE_DATA") or "").strip()

    if flet_storage:
        target = Path(flet_storage).expanduser().resolve() / "logs"
    elif sys.platform.startswith("linux") and is_flet_build():
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        target = Path(xdg_config) / APP_ARTIFACT / "logs"
    elif sys.platform.startswith("win") and is_flet_build():
        local_app_data = os.environ.get(
            "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
        )
        target = Path(local_app_data) / APP_ARTIFACT / "logs"
    else:
        target = project_root() / "logs"

    target.mkdir(parents=True, exist_ok=True)
    return target


def console_log_path() -> Path | None:
    value = str(os.environ.get("FLET_APP_CONSOLE") or "").strip()
    return Path(value).expanduser().resolve() if value else None


def executable_dir() -> Path:
    """Directorio base del ejecutable/launcher."""
    candidate = Path(sys.executable).resolve()
    return candidate.parent


def _prepare(target: Path, *, migrate: bool) -> Path:
    target = target.resolve()
    with _INIT_LOCK:
        target.mkdir(parents=True, exist_ok=True)
        if target in _INITIALIZED_DIRS:
            return target
        if migrate:
            _migrate_legacy_json(target)
        _INITIALIZED_DIRS.add(target)
    return target


def _migrate_legacy_json(target: Path) -> None:
    """Migra configuraciones de desarrollo en el primer arranque empaquetado."""
    if any(p.is_file() and not p.name.endswith(".example.json") for p in target.glob("*.json")):
        return

    for source in _legacy_candidates():
        try:
            source = source.resolve()
        except Exception:
            continue
        if source == target or not source.is_dir():
            continue

        copied = 0
        for path in source.glob("*.json"):
            if not path.is_file() or path.name.endswith(".example.json"):
                continue
            destination = target / path.name
            if destination.exists():
                continue
            try:
                shutil.copy2(path, destination)
                copied += 1
            except OSError:
                continue
        if copied:
            logging.info(
                "[Config] Migrados %s archivos desde %s hacia %s",
                copied,
                source,
                target,
            )
            return


def _legacy_candidates() -> list[Path]:
    candidates: list[Path] = []

    explicit = str(os.environ.get("WIZZ_LEGACY_CONFIG_DIR") or "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())

    candidates.extend(
        [
            Path.cwd() / "config" / "json",
            executable_dir() / "config" / "json",
            project_root() / "config" / "json",
            executable_dir() / APP_ARTIFACT / "config" / "json",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        key = os.path.normcase(os.path.abspath(str(item)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
