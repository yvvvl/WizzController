from core.platform import PlatformServices, build_platform_services


def test_linux_composition_selects_linux_services(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    services = build_platform_services("linux")

    assert isinstance(services, PlatformServices)
    assert services.tray is not None
    assert services.autostart is not None
    assert services.window is not None
    assert services.system is not None


def test_unknown_platform_is_safe_and_unavailable():
    services = build_platform_services("darwin")

    assert services.tray is None
    assert not services.capabilities.tray.is_usable
    assert "darwin" in (services.capabilities.tray.reason or "")
