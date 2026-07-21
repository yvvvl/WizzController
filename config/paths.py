"""Rutas persistentes y assets para desarrollo y builds de Flet.

En desarrollo se conserva el comportamiento histórico y los JSON viven en
``config/json`` dentro del repositorio. En una app generada con ``flet build``
se usa ``FLET_APP_STORAGE_DATA``, que Flet mantiene entre actualizaciones.

Se admite ``WIZZ_CONFIG_DIR`` como override exacto para tests, diagnósticos y
modo portable controlado.
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
    return bool(
        str(os.environ.get("FLET_APP_STORAGE_DATA") or "").strip()
        or getattr(sys, "frozen", False)
    )


def config_dir() -> Path:
    """Directorio writable para los JSON reales de la aplicación."""

    override = str(os.environ.get("WIZZ_CONFIG_DIR") or "").strip()
    if override:
        target = Path(override).expanduser().resolve()
        return _prepare(target, migrate=False)

    flet_storage = str(os.environ.get("FLET_APP_STORAGE_DATA") or "").strip()
    if flet_storage:
        target = Path(flet_storage).expanduser().resolve() / "config"
        return _prepare(target, migrate=True)

    # Compatibilidad con el flujo actual ``python main.py``.
    target = project_root() / "config" / "json"
    return _prepare(target, migrate=False)


def logs_dir() -> Path:
    flet_storage = str(os.environ.get("FLET_APP_STORAGE_DATA") or "").strip()
    if flet_storage:
        target = Path(flet_storage).expanduser().resolve() / "logs"
    else:
        target = project_root() / "logs"
    target.mkdir(parents=True, exist_ok=True)
    return target


def console_log_path() -> Path | None:
    value = str(os.environ.get("FLET_APP_CONSOLE") or "").strip()
    return Path(value).expanduser().resolve() if value else None


def executable_dir() -> Path:
    """Mejor aproximación al directorio del launcher actual."""

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
    """Copia config dev existente en el primer arranque empaquetado.

    Solo actúa cuando el destino aún no tiene JSON reales. No copia ejemplos ni
    sobrescribe archivos. Es útil cuando el ejecutable se prueba desde el mismo
    repositorio que antes se ejecutaba con ``python main.py``.
    """

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
