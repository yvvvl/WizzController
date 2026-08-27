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
    LinuxTrayBackend,
    LinuxWindowService,
    detect_linux_capabilities,
)
from .composition import PlatformServices, build_platform_services

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
    "LinuxTrayBackend",
    "LinuxWindowService",
    "HotkeyService",
    "SingleInstanceService",
    "SystemIntegrationService",
    "TrayBackend",
    "WindowService",
    "detect_linux_capabilities",
    "PlatformServices",
    "build_platform_services",
]
