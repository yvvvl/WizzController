from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from qt_ui import run
from core import dev_virtual_lights
from core.dev_virtual_lights import ENV_NAME, VirtualLightController
from PySide6.QtCore import QCoreApplication


def test_wayland_runtime_prefers_xwayland_when_xcb_libraries_exist(monkeypatch):
    monkeypatch.setattr(run.sys, "platform", "linux")
    monkeypatch.setattr(run, "find_library", lambda _name: "/usr/lib/libxcb.so")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)

    assert run._prefer_xcb_for_wayland() is True
    assert run.os.environ["QT_QPA_PLATFORM"] == "xcb"


def test_wayland_runtime_keeps_safe_backend_when_xcb_libraries_are_missing(monkeypatch):
    monkeypatch.setattr(run.sys, "platform", "linux")
    monkeypatch.setattr(run, "find_library", lambda _name: None)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)

    assert run._prefer_xcb_for_wayland() is False
    assert "QT_QPA_PLATFORM" not in run.os.environ


def test_wayland_runtime_respects_explicit_qpa_choice(monkeypatch):
    monkeypatch.setattr(run.sys, "platform", "linux")
    monkeypatch.setattr(run, "find_library", lambda _name: "/usr/lib/libxcb.so")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("QT_QPA_PLATFORM", "wayland")

    assert run._prefer_xcb_for_wayland() is False
    assert run.os.environ["QT_QPA_PLATFORM"] == "wayland"


def test_qt_controller_factory_uses_real_lights(monkeypatch):
    monkeypatch.delenv(ENV_NAME, raising=False)
    sentinel = object()
    monkeypatch.setattr(run, "LightController", lambda: sentinel)

    assert run.create_controller() is sentinel


def test_qt_controller_factory_uses_virtual_lights_only_when_requested(monkeypatch):
    monkeypatch.setenv(ENV_NAME, "3")
    controller = run.create_controller()

    assert isinstance(controller, VirtualLightController)
    assert len(controller.get_bulbs_detailed()) == 3
    assert controller.proto is None


def test_qt_virtual_profile_is_separate_from_real_settings(monkeypatch):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", "real-user-profile")
    run._prepare_virtual_profile(3)
    assert "WizZDesktop-virtual-qt" in str(run.os.environ["WIZZ_CONFIG_DIR"])
    assert run.os.environ["WIZZ_CONFIG_DIR"] != "real-user-profile"


def test_virtual_runtime_restores_tray_after_old_qa_profile_disabled_it():
    class Settings:
        def __init__(self):
            self.data = {"tray_enabled": False, "open_minimized": True}

        def update(self, **values):
            self.data.update(values)

    settings = Settings()
    run._prepare_virtual_runtime_settings(settings, 3)
    assert settings.data == {"tray_enabled": True, "open_minimized": True}

    real_settings = Settings()
    run._prepare_virtual_runtime_settings(real_settings, 0)
    assert real_settings.data == {"tray_enabled": False, "open_minimized": True}


def test_packaged_qt_build_ignores_virtual_light_request(monkeypatch):
    monkeypatch.setenv(ENV_NAME, "3")
    monkeypatch.setattr(dev_virtual_lights, "is_packaged_desktop_build", lambda: True)
    sentinel = object()
    monkeypatch.setattr(run, "LightController", lambda: sentinel)

    assert run.create_controller() is sentinel


def test_restarted_app_keeps_waiting_for_detached_update_result():
    app = QCoreApplication.instance() or QCoreApplication([])

    class Bridge:
        def __init__(self):
            self.checks = 0

        def loadUpdateCompletion(self):
            self.checks += 1
            return self.checks == 7

    bridge = Bridge()
    timer = run._watch_update_completion(app, bridge)
    try:
        for _ in range(6):
            timer.timeout.emit()
            assert timer.isActive()
        timer.timeout.emit()
        assert bridge.checks == 7
        assert not timer.isActive()
    finally:
        timer.stop()


def test_update_completion_wait_is_bounded():
    app = QCoreApplication.instance() or QCoreApplication([])

    class Bridge:
        def __init__(self):
            self.checks = 0

        def loadUpdateCompletion(self):
            self.checks += 1
            return False

    bridge = Bridge()
    timer = run._watch_update_completion(app, bridge)
    try:
        for _ in range(120):
            timer.timeout.emit()
        assert bridge.checks == 120
        assert not timer.isActive()
    finally:
        timer.stop()
