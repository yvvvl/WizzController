"""Opt-in runtime facade for desktop platform services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .composition import PlatformServices, build_platform_services


@dataclass(slots=True)
class PlatformRuntime:
    """Coordinate optional desktop services without starting them implicitly."""

    services: PlatformServices

    @classmethod
    def create(cls, platform: str | None = None) -> "PlatformRuntime":
        return cls(build_platform_services(platform))

    @property
    def capabilities(self):
        return self.services.capabilities

    def start_tray(self, menu: Sequence[object]) -> bool:
        tray = self.services.tray
        if tray is None:
            return False
        return bool(tray.start(menu))

    def stop(self) -> None:
        tray = self.services.tray
        if tray is not None:
            tray.stop()


__all__ = ["PlatformRuntime"]
