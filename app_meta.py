"""Metadatos únicos de WizZ Desktop.

Este módulo no importa Flet ni dependencias de escritorio. Se usa tanto en
runtime como en tests y scripts de build para mantener nombre, versión e ID en
un solo lugar.
"""

from __future__ import annotations

APP_NAME = "WizZ Desktop"
APP_PRODUCT = "WizZ Desktop"
APP_ARTIFACT = "WizZDesktop"
APP_ID = "WizZDesktop"
APP_REGISTRY_NAME = "WizZController"
APP_VERSION = "1.1.0"
APP_BUILD_NUMBER = 1
APP_DESCRIPTION = "Control local de ampolletas WiZ por LAN."
APP_COMPANY = "yvvvl"
APP_COPYRIGHT = "Copyright © 2026 Ignacio"


def display_version() -> str:
    """Versión legible para UI, logs y documentación."""

    return f"v{APP_VERSION} (build {APP_BUILD_NUMBER})"
