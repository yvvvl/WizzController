import json
from pathlib import Path

from config.app_runtime_manager import AppRuntimeManager


def test_runtime_keeps_only_supported_keys(tmp_path):
    manager = AppRuntimeManager.__new__(AppRuntimeManager)
    manager.base_dir = Path(tmp_path)
    manager.json_dir = Path(tmp_path)
    manager.path = Path(tmp_path) / "app_runtime.json"
    manager.path.write_text(
        json.dumps(
            {
                "old_feature_toggle": True,
                "tray_enabled": False,
                "minimize_to_tray": False,
                "open_minimized": True,
                "startup_with_windows": False,
            }
        ),
        encoding="utf-8",
    )

    data = manager._load()
    saved = json.loads(manager.path.read_text(encoding="utf-8"))

    assert "old_feature_toggle" not in data
    assert "old_feature_toggle" not in saved
    assert data["tray_enabled"] is False
    assert data["open_minimized"] is True


def _runtime_manager_for_test(tmp_path):
    import threading

    manager = AppRuntimeManager.__new__(AppRuntimeManager)
    manager.base_dir = tmp_path
    manager.json_dir = tmp_path
    manager.path = tmp_path / "app_runtime.json"
    manager._lock = threading.RLock()
    manager.data = dict(AppRuntimeManager.DEFAULTS)
    return manager


def test_linux_startup_uses_xdg_service_and_preserves_legacy_preference(monkeypatch, tmp_path):
    import config.app_runtime_manager as runtime_module

    manager = _runtime_manager_for_test(tmp_path)
    monkeypatch.setattr(runtime_module.sys, "platform", "linux")

    calls = []

    class _LinuxAutostart:
        def set_enabled(self, enabled):
            calls.append(enabled)
            return True

    monkeypatch.setattr(manager, "_linux_autostart_service", lambda: _LinuxAutostart())

    ok, _message = manager.set_startup_with_windows(True)

    assert ok is True
    assert calls == [True]
    assert manager.data["startup_with_windows"] is True


def test_linux_startup_does_not_claim_enabled_when_xdg_entry_fails(monkeypatch, tmp_path):
    import config.app_runtime_manager as runtime_module

    manager = _runtime_manager_for_test(tmp_path)
    monkeypatch.setattr(runtime_module.sys, "platform", "linux")

    class _UnavailableAutostart:
        def set_enabled(self, enabled):
            return False

    monkeypatch.setattr(manager, "_linux_autostart_service", lambda: _UnavailableAutostart())

    ok, _message = manager.set_startup_with_windows(True)

    assert ok is False
    assert manager.data["startup_with_windows"] is False
