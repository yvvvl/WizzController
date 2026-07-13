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
