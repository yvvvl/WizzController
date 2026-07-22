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


def test_flet_storage_migrates_legacy_json_once(monkeypatch, tmp_path):
    storage = tmp_path / "app-data"
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "hotkeys.json").write_text(json.dumps({"enabled": True}), encoding="utf-8")
    (legacy / "hotkeys.example.json").write_text("{}", encoding="utf-8")

    monkeypatch.delenv("WIZZ_CONFIG_DIR", raising=False)
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(storage))
    monkeypatch.setenv("WIZZ_LEGACY_CONFIG_DIR", str(legacy))
    _reset_paths()

    target = paths.config_dir()
    assert target == (storage / "config").resolve()
    assert json.loads((target / "hotkeys.json").read_text(encoding="utf-8")) == {"enabled": True}
    assert not (target / "hotkeys.example.json").exists()

    # No sobrescribe datos ya persistidos en un siguiente acceso.
    (target / "hotkeys.json").write_text(json.dumps({"enabled": False}), encoding="utf-8")
    _reset_paths()
    assert paths.config_dir() == target
    assert json.loads((target / "hotkeys.json").read_text(encoding="utf-8")) == {"enabled": False}


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
