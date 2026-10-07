from __future__ import annotations

from pathlib import Path, PurePosixPath

import config.app_runtime_manager as runtime_module
from config.app_runtime_manager import AppRuntimeManager, resolve_packaged_executable


def test_explicit_packaged_executable_override(monkeypatch, tmp_path):
    executable = tmp_path / "WizZDesktop.exe"
    executable.write_bytes(b"test")
    monkeypatch.setenv("WIZZ_EXECUTABLE", str(executable))

    assert resolve_packaged_executable() == executable.resolve()


def test_linux_packaged_executable_is_the_frozen_launcher(monkeypatch, tmp_path):
    executable = tmp_path / "WizZDesktop"
    executable.write_bytes(b"test")
    monkeypatch.delenv("WIZZ_EXECUTABLE", raising=False)
    monkeypatch.setattr(runtime_module.sys, "platform", "linux")
    monkeypatch.setattr(runtime_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime_module.sys, "executable", str(executable))

    assert resolve_packaged_executable() == executable.resolve()
    monkeypatch.setattr(runtime_module.sys, "frozen", False)
    assert resolve_packaged_executable() is None


def test_linux_autostart_uses_desktop_exec_quoting(monkeypatch):
    executable = PurePosixPath("/home/yvl/WizZ Desktop 100%/WizZDesktop")
    monkeypatch.setattr(runtime_module.sys, "platform", "linux")
    monkeypatch.setattr(runtime_module, "resolve_packaged_executable", lambda: executable)

    manager = AppRuntimeManager.__new__(AppRuntimeManager)
    assert manager._startup_command() == '"/home/yvl/WizZ Desktop 100%%/WizZDesktop"'


def test_startup_command_prefers_packaged_launcher(monkeypatch, tmp_path):
    executable = tmp_path / "WizZ Desktop" / "WizZDesktop.exe"
    monkeypatch.setattr(runtime_module, "resolve_packaged_executable", lambda: executable)

    manager = AppRuntimeManager.__new__(AppRuntimeManager)
    command = manager._startup_command()

    assert str(executable) in command
    assert "main.py" not in command
    assert "python" not in Path(str(executable)).name.casefold()


def _runtime_manager_for_test(tmp_path):
    import threading

    manager = AppRuntimeManager.__new__(AppRuntimeManager)
    manager.base_dir = tmp_path
    manager.json_dir = tmp_path
    manager.path = tmp_path / "app_runtime.json"
    manager._lock = threading.RLock()
    manager.data = dict(AppRuntimeManager.DEFAULTS)
    return manager


def test_startup_flag_is_saved_only_after_registry_success(monkeypatch, tmp_path):
    manager = _runtime_manager_for_test(tmp_path)
    monkeypatch.setattr(runtime_module.sys, "platform", "win32")
    monkeypatch.setattr(manager, "_startup_command", lambda: '"C:\\Apps\\WizZDesktop.exe"')

    written = []
    monkeypatch.setattr(runtime_module, "_write_startup_value", written.append)

    ok, _message = manager.set_startup_with_windows(True)

    assert ok is True
    assert written == ['"C:\\Apps\\WizZDesktop.exe"']
    assert manager.data["startup_with_windows"] is True


def test_startup_flag_is_not_enabled_when_registry_write_fails(monkeypatch, tmp_path):
    manager = _runtime_manager_for_test(tmp_path)
    monkeypatch.setattr(runtime_module.sys, "platform", "win32")
    monkeypatch.setattr(manager, "_startup_command", lambda: '"C:\\Apps\\WizZDesktop.exe"')

    def fail(_command):
        raise PermissionError("registro bloqueado")

    monkeypatch.setattr(runtime_module, "_write_startup_value", fail)

    ok, message = manager.set_startup_with_windows(True)

    assert ok is False
    assert "registro bloqueado" in message
    assert manager.data["startup_with_windows"] is False


def test_source_checkout_does_not_replace_packaged_startup_entry(monkeypatch, tmp_path):
    manager = _runtime_manager_for_test(tmp_path)
    manager.data["startup_with_windows"] = True
    monkeypatch.setattr(runtime_module.sys, "platform", "win32")
    monkeypatch.setattr(runtime_module, "resolve_packaged_executable", lambda: None)
    monkeypatch.setattr(runtime_module, "_read_startup_value", lambda: '"C:\\Apps\\WizZDesktop.exe"')
    written = []
    monkeypatch.setattr(runtime_module, "_write_startup_value", written.append)

    manager._sync_startup_registration()

    assert written == []


def test_disabling_windows_startup_removes_registration(monkeypatch, tmp_path):
    manager = _runtime_manager_for_test(tmp_path)
    manager.data["startup_with_windows"] = True
    monkeypatch.setattr(runtime_module.sys, "platform", "win32")
    removed = []
    monkeypatch.setattr(runtime_module, "_delete_startup_value", lambda: removed.append(True))

    ok, _message = manager.set_startup_with_windows(False)

    assert ok is True
    assert removed == [True]
    assert manager.data["startup_with_windows"] is False


def test_linux_source_checkout_does_not_replace_autostart_entry(monkeypatch, tmp_path):
    manager = _runtime_manager_for_test(tmp_path)
    manager.data["startup_with_windows"] = True
    monkeypatch.setattr(runtime_module.sys, "platform", "linux")
    monkeypatch.setattr(runtime_module, "resolve_packaged_executable", lambda: None)
    calls = []
    monkeypatch.setattr(manager, "_linux_autostart_service", lambda: calls.append(True))

    manager._sync_startup_registration()

    assert calls == []
