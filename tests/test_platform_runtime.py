from core.platform import PlatformRuntime
from core.platform.capabilities import CapabilityState, DesktopCapabilities
from core.platform.fakes import FakeTrayBackend


def test_runtime_does_not_start_services_implicitly():
    runtime = PlatformRuntime.create("darwin")

    assert runtime.services.tray is None
    assert not runtime.capabilities.tray.is_usable


def test_runtime_delegates_tray_lifecycle():
    caps = DesktopCapabilities(tray=CapabilityState.available("test"))
    tray = FakeTrayBackend(capabilities=caps)
    services = PlatformRuntime.create("darwin").services
    services = services.__class__(
        capabilities=services.capabilities,
        tray=tray,
    )
    runtime = PlatformRuntime(services)

    assert runtime.start_tray(["quit"])
    assert tray.running
    runtime.stop()
    assert not tray.running
