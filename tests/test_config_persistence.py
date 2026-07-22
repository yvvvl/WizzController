from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json

import config.config_manager as config_module
from config.config_manager import ConfigManager


def test_config_save_retries_transient_replace_lock(
    monkeypatch,
    tmp_path,
):
    path = tmp_path / "config.json"
    manager = ConfigManager(path)

    real_replace = config_module.os.replace
    attempts = {"count": 0}

    def flaky_replace(source, destination):
        attempts["count"] += 1

        if attempts["count"] < 3:
            raise PermissionError("archivo temporalmente bloqueado")

        return real_replace(source, destination)

    monkeypatch.setattr(
        config_module.os,
        "replace",
        flaky_replace,
    )

    manager.set("probe", {"ok": True})

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["probe"] == {"ok": True}
    assert attempts["count"] == 3


def test_concurrent_config_managers_keep_valid_json(tmp_path):
    path = tmp_path / "config.json"
    ConfigManager(path)

    def write_value(index: int) -> None:
        manager = ConfigManager(path)
        manager.set(f"stress_{index % 12}", index)

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(write_value, range(300)))

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert isinstance(payload, dict)

    for index in range(12):
        assert f"stress_{index}" in payload

    leftovers = list(tmp_path.glob("config.json.*.tmp"))
    assert leftovers == []
