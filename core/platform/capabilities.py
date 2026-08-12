"""Immutable models describing effective desktop integration support."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum


class CapabilityStatus(str, Enum):
    """Availability state for one desktop capability."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    PERMISSION_REQUIRED = "permission_required"


@dataclass(frozen=True, slots=True)
class CapabilityState:
    """Immutable state and optional explanation for one capability."""

    status: CapabilityStatus | str
    reason: str | None = None

    def __post_init__(self) -> None:
        try:
            status = CapabilityStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"unknown capability status: {self.status!r}"
            ) from exc

        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("capability reason must be text or None")

        reason = self.reason.strip() if self.reason is not None else None
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason", reason or None)

    @classmethod
    def available(cls, reason: str | None = None) -> CapabilityState:
        return cls(CapabilityStatus.AVAILABLE, reason)

    @classmethod
    def unavailable(cls, reason: str | None = None) -> CapabilityState:
        return cls(CapabilityStatus.UNAVAILABLE, reason)

    @classmethod
    def degraded(cls, reason: str | None = None) -> CapabilityState:
        return cls(CapabilityStatus.DEGRADED, reason)

    @classmethod
    def permission_required(
        cls,
        reason: str | None = None,
    ) -> CapabilityState:
        return cls(CapabilityStatus.PERMISSION_REQUIRED, reason)

    @property
    def is_available(self) -> bool:
        return self.status is CapabilityStatus.AVAILABLE

    @property
    def is_usable(self) -> bool:
        return self.status in {
            CapabilityStatus.AVAILABLE,
            CapabilityStatus.DEGRADED,
        }


def _unavailable() -> CapabilityState:
    return CapabilityState.unavailable()


@dataclass(frozen=True, slots=True)
class DesktopCapabilities:
    """Effective desktop capabilities for one concrete runtime session."""

    hotkey_registration: CapabilityState = field(
        default_factory=_unavailable
    )
    hotkey_recording: CapabilityState = field(default_factory=_unavailable)
    tray: CapabilityState = field(default_factory=_unavailable)
    tray_default_action: CapabilityState = field(
        default_factory=_unavailable
    )
    start_at_login: CapabilityState = field(default_factory=_unavailable)
    window_show: CapabilityState = field(default_factory=_unavailable)
    window_hide: CapabilityState = field(default_factory=_unavailable)
    window_restore: CapabilityState = field(default_factory=_unavailable)
    window_focus: CapabilityState = field(default_factory=_unavailable)
    work_area_positioning: CapabilityState = field(
        default_factory=_unavailable
    )
    frameless: CapabilityState = field(default_factory=_unavailable)
    always_on_top: CapabilityState = field(default_factory=_unavailable)
    taskbar_skip: CapabilityState = field(default_factory=_unavailable)
    single_instance_exclusion: CapabilityState = field(
        default_factory=_unavailable
    )
    single_instance_activation: CapabilityState = field(
        default_factory=_unavailable
    )
    open_folder: CapabilityState = field(default_factory=_unavailable)

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if not isinstance(value, CapabilityState):
                raise TypeError(
                    f"{item.name} must be a CapabilityState"
                )
