from __future__ import annotations

import json
from pathlib import Path

from config import paths
from config.base_manager import JsonManager


def _reset_paths() -> None:
    paths._INITIALIZED_DIRS.clear()


def test_config_dir_override_is_exact(monkeypatch, tmp_path):
    target = tmp_path / "portable-config"
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(target))
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    _reset_paths()

    assert paths.config_dir() == target.resolve()
    assert target.is_dir()


def test_linux_packaged_build_uses_xdg_and_migrates_flet_storage(monkeypatch, tmp_path):
    storage = tmp_path / "app-data"
    legacy = storage / "config"
    legacy.mkdir(parents=True)
    (legacy / "hotkeys.json").write_text(json.dumps({"enabled": True}), encoding="utf-8")
    (legacy / "hotkeys.example.json").write_text("{}", encoding="utf-8")
    xdg_config = tmp_path / "xdg-config"
    xdg_state = tmp_path / "xdg-state"

    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(storage))
    monkeypatch.delenv("WIZZ_LEGACY_CONFIG_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg_state))
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "platform", "linux")
    _reset_paths()

    target = paths.config_dir()
    assert target == (xdg_config / paths.APP_ARTIFACT / "config").resolve()
    assert json.loads((target / "hotkeys.json").read_text(encoding="utf-8")) == {"enabled": True}
    assert not (target / "hotkeys.example.json").exists()

    # No sobrescribe datos ya persistidos en un siguiente acceso.
    (target / "hotkeys.json").write_text(json.dumps({"enabled": False}), encoding="utf-8")
    _reset_paths()
    assert paths.config_dir() == target
    assert json.loads((target / "hotkeys.json").read_text(encoding="utf-8")) == {"enabled": False}
    assert paths.logs_dir() == (xdg_state / paths.APP_ARTIFACT / "logs").resolve()


def test_windows_frozen_build_uses_local_appdata(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "config.json").write_text("{\"language\": \"es\"}", encoding="utf-8")

    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("WIZZ_LEGACY_CONFIG_DIR", str(legacy))
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    _reset_paths()

    target = paths.config_dir()
    assert target == (local_app_data / paths.APP_ARTIFACT / "config").resolve()
    assert (target / "config.json").exists()


def test_windows_packaged_flet_runtime_uses_local_appdata_and_migrates(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    flet_storage = tmp_path / "DocumentsFlet"
    legacy_config = flet_storage / "config"
    legacy_config.mkdir(parents=True)
    (legacy_config / "favorites.json").write_text("[]", encoding="utf-8")

    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(flet_storage))
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    _reset_paths()

    assert paths.config_dir() == (local_app_data / paths.APP_ARTIFACT / "config").resolve()
    assert (paths.config_dir() / "favorites.json").exists()
    assert paths.logs_dir() == (local_app_data / paths.APP_ARTIFACT / "logs").resolve()


def test_windows_packaged_executable_is_detected_without_frozen_flag(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setattr(paths.sys, "executable", str(tmp_path / "WizZDesktop.exe"))
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)
    _reset_paths()

    assert paths.is_flet_build()
    assert paths.config_dir() == (local_app_data / paths.APP_ARTIFACT / "config").resolve()


def test_windows_embedded_runtime_detects_neighboring_app_executable(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    runtime_dir = tmp_path / "build" / "windows"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "WizZDesktop.exe").write_bytes(b"marker")
    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setattr(paths.sys, "executable", str(runtime_dir / "python.exe"))
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)
    _reset_paths()

    assert paths.is_flet_build()
    assert paths.config_dir() == (local_app_data / paths.APP_ARTIFACT / "config").resolve()


def test_windows_launcher_argument_detects_packaged_runtime(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setattr(paths.sys, "executable", str(tmp_path / "python.exe"))
    monkeypatch.setattr(paths.sys, "argv", [str(tmp_path / "WizZDesktop.exe")])
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)
    _reset_paths()

    assert paths.is_flet_build()
    assert paths.config_dir() == (local_app_data / paths.APP_ARTIFACT / "config").resolve()


def test_flet_embedded_app_zip_detects_packaged_runtime(monkeypatch, tmp_path):
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setattr(paths.sys, "executable", str(tmp_path / "python.exe"))
    monkeypatch.setattr(paths.sys, "argv", ["main.py"])
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)
    monkeypatch.setattr(
        paths,
        "__file__",
        str(tmp_path / "flutter_assets" / "app.zip" / "config" / "paths.pyc"),
    )
    _reset_paths()

    assert paths.is_flet_build()
    assert paths.config_dir() == (local_app_data / paths.APP_ARTIFACT / "config").resolve()


def test_json_manager_uses_override_and_atomic_save(monkeypatch, tmp_path):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    _reset_paths()

    manager = JsonManager("sample.json", default_data={"value": 1})
    manager.data["value"] = 2
    manager.save()

    assert Path(manager.filepath) == tmp_path / "sample.json"
    assert json.loads((tmp_path / "sample.json").read_text(encoding="utf-8")) == {"value": 2}
    assert not list(tmp_path.glob("*.tmp"))


def test_config_managers_merge_independent_keys(monkeypatch, tmp_path):
    from config.config_manager import ConfigManager

    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    _reset_paths()

    core_config = ConfigManager()
    color_config = ConfigManager()

    core_config.set("removed_bulbs", [{"ip": "192.168.1.44", "mac": "aabbccddeeff"}])
    color_config.set("color_picker", {"apply_live": False})

    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["removed_bulbs"] == [
        {"ip": "192.168.1.44", "mac": "aabbccddeeff"}
    ]
    assert saved["color_picker"] == {"apply_live": False}
