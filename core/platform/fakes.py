"""Deterministic in-memory implementations of the platform contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .capabilities import DesktopCapabilities
from .contracts import HotkeyCallback, TrayMenu, WorkArea


@dataclass(slots=True)
class FakeHotkeyService:
    capabilities: DesktopCapabilities = field(
        default_factory=DesktopCapabilities
    )
    recorded_shortcut: str | None = None
    registrations: dict[str, HotkeyCallback] = field(
        default_factory=dict,
        init=False,
    )

    def register(
        self,
        shortcut: str,
        callback: HotkeyCallback,
    ) -> bool:
        normalized = str(shortcut or "").strip()
        if (
            not normalized
            or not callable(callback)
            or not self.capabilities.hotkey_registration.is_usable
        ):
            return False
        self.registrations[normalized] = callback
        return True

    def unregister(self, shortcut: str) -> bool:
        normalized = str(shortcut or "").strip()
        return self.registrations.pop(normalized, None) is not None

    def record(self) -> str | None:
        if not self.capabilities.hotkey_recording.is_usable:
            return None
        normalized = str(self.recorded_shortcut or "").strip()
        return normalized or None

    def trigger(self, shortcut: str) -> bool:
        callback = self.registrations.get(str(shortcut or "").strip())
        if callback is None:
            return False
        callback()
        return True


@dataclass(slots=True)
class FakeTrayBackend:
    capabilities: DesktopCapabilities = field(
        default_factory=DesktopCapabilities
    )
    menu: tuple[object, ...] = field(default=(), init=False)
    running: bool = field(default=False, init=False)

    def start(self, menu: TrayMenu) -> bool:
        if not self.capabilities.tray.is_usable:
            return False
        self.menu = tuple(menu)
        self.running = True
        return True

    def update_menu(self, menu: TrayMenu) -> bool:
        if not self.running or not self.capabilities.tray.is_usable:
            return False
        self.menu = tuple(menu)
        return True

    def stop(self) -> None:
        self.running = False


@dataclass(slots=True)
class FakeAutostartService:
    capabilities: DesktopCapabilities = field(
        default_factory=DesktopCapabilities
    )
    enabled: bool = False

    def is_enabled(self) -> bool:
        return self.enabled

    def set_enabled(self, enabled: bool) -> bool:
        if not self.capabilities.start_at_login.is_usable:
            return False
        self.enabled = bool(enabled)
        return True


@dataclass(slots=True)
class FakeWindowService:
    capabilities: DesktopCapabilities = field(
        default_factory=DesktopCapabilities
    )
    work_area: WorkArea | None = None
    calls: list[str] = field(default_factory=list, init=False)

    def show(self) -> bool:
        return self._perform("show", "window_show")

    def hide(self) -> bool:
        return self._perform("hide", "window_hide")

    def restore(self) -> bool:
        return self._perform("restore", "window_restore")

    def focus(self) -> bool:
        return self._perform("focus", "window_focus")

    def get_work_area(self) -> WorkArea | None:
        if not self.capabilities.work_area_positioning.is_usable:
            return None
        self.calls.append("get_work_area")
        return self.work_area

    def _perform(self, operation: str, capability_name: str) -> bool:
        state = getattr(self.capabilities, capability_name)
        if not state.is_usable:
            return False
        self.calls.append(operation)
        return True


@dataclass(slots=True)
class FakeSingleInstanceService:
    capabilities: DesktopCapabilities = field(
        default_factory=DesktopCapabilities
    )
    acquisition_result: bool = True
    activation_result: bool = True
    is_owner: bool = field(default=False, init=False)
    activation_requests: int = field(default=0, init=False)

    def acquire(self) -> bool:
        if self.is_owner:
            return True
        if (
            not self.capabilities.single_instance_exclusion.is_usable
            or not self.acquisition_result
        ):
            return False
        self.is_owner = True
        return True

    def release(self) -> None:
        self.is_owner = False

    def activate_existing(self) -> bool:
        if (
            not self.capabilities.single_instance_activation.is_usable
            or not self.activation_result
        ):
            return False
        self.activation_requests += 1
        return True


@dataclass(slots=True)
class FakeSystemIntegrationService:
    capabilities: DesktopCapabilities = field(
        default_factory=DesktopCapabilities
    )
    opened_folders: list[Path] = field(default_factory=list, init=False)

    def open_folder(self, path: str | Path) -> bool:
        if not self.capabilities.open_folder.is_usable:
            return False
        self.opened_folders.append(Path(path))
        return True


__all__ = [
    "FakeAutostartService",
    "FakeHotkeyService",
    "FakeSingleInstanceService",
    "FakeSystemIntegrationService",
    "FakeTrayBackend",
    "FakeWindowService",
]
