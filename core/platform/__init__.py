"""Platform-neutral desktop capability and service boundaries."""

from .capabilities import (
    CapabilityState,
    CapabilityStatus,
    DesktopCapabilities,
)
from .contracts import (
    AutostartService,
    HotkeyService,
    SingleInstanceService,
    SystemIntegrationService,
    TrayBackend,
    WindowService,
)
from .fakes import (
    FakeAutostartService,
    FakeHotkeyService,
    FakeSingleInstanceService,
    FakeSystemIntegrationService,
    FakeTrayBackend,
    FakeWindowService,
)

__all__ = [
    "AutostartService",
    "CapabilityState",
    "CapabilityStatus",
    "DesktopCapabilities",
    "FakeAutostartService",
    "FakeHotkeyService",
    "FakeSingleInstanceService",
    "FakeSystemIntegrationService",
    "FakeTrayBackend",
    "FakeWindowService",
    "HotkeyService",
    "SingleInstanceService",
    "SystemIntegrationService",
    "TrayBackend",
    "WindowService",
]
