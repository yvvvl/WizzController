"""Composition helpers for selecting platform services at the app boundary."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from .capabilities import CapabilityState, DesktopCapabilities
from .linux import (
    LinuxAutostartService,
    LinuxSystemIntegrationService,
    LinuxTrayBackend,
    LinuxWindowService,
    detect_linux_capabilities,
)


@dataclass(frozen=True, slots=True)
class PlatformServices:
    """Selected optional desktop services; consumers remain capability-driven."""

    capabilities: DesktopCapabilities
    tray: Any | None = None
    autostart: Any | None = None
    window: Any | None = None
    system: Any | None = None


def build_platform_services(platform: str | None = None) -> PlatformServices:
    """Build services without changing existing platform-specific runtime code."""
    target = platform or sys.platform
    if target.startswith("linux"):
        capabilities = detect_linux_capabilities()
        return PlatformServices(
            capabilities=capabilities,
            tray=LinuxTrayBackend(capabilities=capabilities),
            autostart=LinuxAutostartService(desktop_entry="wizz-desktop"),
            window=LinuxWindowService(capabilities=capabilities),
            system=LinuxSystemIntegrationService(capabilities=capabilities),
        )
    unavailable = CapabilityState.unavailable(
        f"platform services are not implemented for {target}"
    )
    capabilities = DesktopCapabilities(
        **{name: unavailable for name in DesktopCapabilities.__dataclass_fields__}
    )
    return PlatformServices(capabilities=capabilities)


__all__ = ["PlatformServices", "build_platform_services"]
