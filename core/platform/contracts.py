"""Platform-neutral contracts for optional desktop integrations."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol, Sequence, runtime_checkable

from .capabilities import DesktopCapabilities

HotkeyCallback = Callable[[], None]
TrayMenu = Sequence[object]
WorkArea = tuple[int, int, int, int]


@runtime_checkable
class HotkeyService(Protocol):
    """Register desktop shortcuts without exposing a native backend."""

    @property
    def capabilities(self) -> DesktopCapabilities: ...

    def register(
        self,
        shortcut: str,
        callback: HotkeyCallback,
    ) -> bool: ...

    def unregister(self, shortcut: str) -> bool: ...

    def record(self) -> str | None: ...


@runtime_checkable
class TrayBackend(Protocol):
    """Own a desktop tray or menu-bar icon lifecycle."""

    @property
    def capabilities(self) -> DesktopCapabilities: ...

    @property
    def running(self) -> bool: ...

    def start(self, menu: TrayMenu) -> bool: ...

    def update_menu(self, menu: TrayMenu) -> bool: ...

    def stop(self) -> None: ...


@runtime_checkable
class AutostartService(Protocol):
    """Read and change the effective start-at-login registration."""

    @property
    def capabilities(self) -> DesktopCapabilities: ...

    def is_enabled(self) -> bool: ...

    def set_enabled(self, enabled: bool) -> bool: ...


@runtime_checkable
class WindowService(Protocol):
    """Expose portable window operations and optional work-area lookup."""

    @property
    def capabilities(self) -> DesktopCapabilities: ...

    def show(self) -> bool: ...

    def hide(self) -> bool: ...

    def restore(self) -> bool: ...

    def focus(self) -> bool: ...

    def get_work_area(self) -> WorkArea | None: ...


@runtime_checkable
class SingleInstanceService(Protocol):
    """Keep process exclusion separate from owner activation."""

    @property
    def capabilities(self) -> DesktopCapabilities: ...

    @property
    def is_owner(self) -> bool: ...

    def acquire(self) -> bool: ...

    def release(self) -> None: ...

    def activate_existing(self) -> bool: ...


@runtime_checkable
class SystemIntegrationService(Protocol):
    """Provide small shell integrations without leaking platform APIs."""

    @property
    def capabilities(self) -> DesktopCapabilities: ...

    def open_folder(self, path: str | Path) -> bool: ...


__all__ = [
    "AutostartService",
    "HotkeyCallback",
    "HotkeyService",
    "SingleInstanceService",
    "SystemIntegrationService",
    "TrayBackend",
    "TrayMenu",
    "WindowService",
    "WorkArea",
]
