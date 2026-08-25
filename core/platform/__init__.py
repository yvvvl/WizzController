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
from .linux import (
    LinuxAutostartService,
    LinuxSystemIntegrationService,
    LinuxWindowService,
    detect_linux_capabilities,
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
    "LinuxAutostartService",
    "LinuxSystemIntegrationService",
    "LinuxWindowService",
    "HotkeyService",
    "SingleInstanceService",
    "SystemIntegrationService",
    "TrayBackend",
    "WindowService",
    "detect_linux_capabilities",
]
