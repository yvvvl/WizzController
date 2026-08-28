import importlib
import os
from pathlib import Path

from core.platform.capabilities import CapabilityStatus, CapabilityState, DesktopCapabilities
from core.platform.linux import (
    LinuxAutostartService,
    LinuxSystemIntegrationService,
    LinuxTrayBackend,
    LinuxWindowService,
    detect_linux_capabilities,
)
from core.background.tray_service import TrayService


def test_linux_capabilities_are_explicit_and_do_not_touch_network(monkeypatch):
    monkeypatch.setattr("core.platform.linux.sys.platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    caps = detect_linux_capabilities()

    assert caps.tray.status is CapabilityStatus.AVAILABLE
    assert caps.hotkey_registration.status is CapabilityStatus.PERMISSION_REQUIRED
    assert caps.start_at_login.status is CapabilityStatus.AVAILABLE
    assert caps.single_instance_activation.status is CapabilityStatus.UNAVAILABLE


def test_linux_autostart_writes_and_removes_user_entry(tmp_path):
    caps = DesktopCapabilities(start_at_login=CapabilityState.available())
    service = LinuxAutostartService(
        "/opt/wizz/WizZDesktop",
        config_home=tmp_path,
        capabilities=caps,
    )

    assert service.set_enabled(True)
    assert service.is_enabled()
    content = service.entry_path.read_text(encoding="utf-8")
    assert "Exec=/opt/wizz/WizZDesktop" in content
    assert service.set_enabled(False)
    assert not service.is_enabled()


def test_linux_autostart_rejects_unusable_capability(tmp_path):
    service = LinuxAutostartService(
        "/opt/wizz/WizZDesktop",
        config_home=tmp_path,
        capabilities=DesktopCapabilities(
            start_at_login=CapabilityState.permission_required("policy")
        ),
    )

    assert not service.set_enabled(True)
    assert not service.entry_path.exists()


def test_linux_system_integration_uses_xdg_open(tmp_path):
    calls = []
    target = Path(tmp_path) / "logs"
    target.mkdir()
    caps = DesktopCapabilities(open_folder=CapabilityState.available("xdg-open"))
    service = LinuxSystemIntegrationService(
        capabilities=caps,
        runner=lambda args: calls.append(args),
    )

    assert service.open_folder(target)
    assert calls == [["xdg-open", str(target.resolve())]]


def test_linux_window_service_delegates_only_usable_operations():
    calls = []
    caps = DesktopCapabilities(
        window_show=CapabilityState.available(),
        window_hide=CapabilityState.degraded("best effort"),
        window_focus=CapabilityState.unavailable("wayland policy"),
        work_area_positioning=CapabilityState.available(),
    )
    service = LinuxWindowService(
        caps,
        show_callback=lambda: calls.append("show") or True,
        hide_callback=lambda: calls.append("hide") or True,
        focus_callback=lambda: calls.append("focus") or True,
        work_area=(0, 0, 1920, 1080),
    )

    assert service.show()
    assert service.hide()
    assert not service.focus()
    assert service.get_work_area() == (0, 0, 1920, 1080)
    assert calls == ["show", "hide"]


class _FakeIcon:
    def __init__(self, menu):
        self.menu = tuple(menu)
        self.stopped = False
        self.started = False

    def run(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _DetachedFakeIcon(_FakeIcon):
    def run_detached(self):
        self.started = True


def test_linux_tray_backend_owns_lifecycle_without_real_desktop():
    created = []

    def factory(menu):
        icon = _FakeIcon(menu)
        created.append(icon)
        return icon

    caps = DesktopCapabilities(
        tray=CapabilityState.available("test desktop")
    )
    backend = LinuxTrayBackend(capabilities=caps, icon_factory=factory)

    assert backend.start(["open", "quit"])
    assert backend.running
    assert created[0].started
    assert backend.update_menu(["open", "settings", "quit"])
    backend.stop()
    assert created[0].stopped
    assert not backend.running


def test_linux_tray_backend_rejects_unavailable_desktop():
    backend = LinuxTrayBackend(capabilities=DesktopCapabilities())

    assert not backend.start([])
    assert not backend.running


def test_linux_tray_backend_prefers_detached_event_loop_when_available():
    created = []

    def factory(menu):
        icon = _DetachedFakeIcon(menu)
        created.append(icon)
        return icon

    backend = LinuxTrayBackend(
        capabilities=DesktopCapabilities(
            tray=CapabilityState.available("test desktop")
        ),
        icon_factory=factory,
    )

    assert backend.start([])
    assert created[0].started
    backend.stop()
    assert created[0].stopped


def test_linux_tray_backend_can_run_foreground_loop():
    created = []

    def factory(menu):
        icon = _FakeIcon(menu)
        created.append(icon)
        return icon

    backend = LinuxTrayBackend(
        capabilities=DesktopCapabilities(
            tray=CapabilityState.available("test desktop")
        ),
        icon_factory=factory,
    )

    assert backend.run_foreground(["quit"])
    assert created[0].started
    assert not backend.running
    assert backend.icon is None


def test_tray_service_prefers_appindicator_on_ubuntu_gnome(monkeypatch):
    tray_module = importlib.import_module("core.background.tray_service")
    monkeypatch.setattr(tray_module.sys, "platform", "linux")
    monkeypatch.delenv("PYSTRAY_BACKEND", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "ubuntu:GNOME")

    TrayService._configure_linux_backend()

    assert os.environ["PYSTRAY_BACKEND"] == "appindicator"


def test_tray_service_keeps_explicit_linux_backend_choice(monkeypatch):
    tray_module = importlib.import_module("core.background.tray_service")
    monkeypatch.setattr(tray_module.sys, "platform", "linux")
    monkeypatch.setenv("PYSTRAY_BACKEND", "xorg")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")

    TrayService._configure_linux_backend()

    assert os.environ["PYSTRAY_BACKEND"] == "xorg"


def test_linux_indicator_icon_is_compact_and_opaque(monkeypatch):
    from PIL import Image, ImageDraw

    tray_module = importlib.import_module("core.background.tray_service")
    monkeypatch.setattr(tray_module.sys, "platform", "linux")

    tray = TrayService(object(), object(), object())
    tray._Image = Image
    tray._ImageDraw = ImageDraw
    image = tray._make_icon()

    assert image.size == (64, 64)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 255


def test_linux_tray_service_runs_appindicator_loop_in_worker_thread(monkeypatch):
    import threading

    tray_module = importlib.import_module("core.background.tray_service")
    tray = TrayService(object(), object(), object())
    started = threading.Event()

    class _Icon:
        def run(self):
            started.set()

        def run_detached(self):  # pragma: no cover - must not be chosen on Linux
            raise AssertionError("Linux must own a worker loop")

    tray.icon = _Icon()
    monkeypatch.setattr(tray_module.sys, "platform", "linux")

    tray._start_icon_loop()

    assert started.wait(1.0)
    assert tray._thread is not None
