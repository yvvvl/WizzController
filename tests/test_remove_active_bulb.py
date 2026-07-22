from __future__ import annotations

import asyncio
from typing import Any

import pytest

from core.light_controller import LightController


IP = "192.168.1.4"
MAC = "cc4085b1209a"


class FakeProto:
    def __init__(self) -> None:
        self.discovered: dict[str, dict[str, Any]] = {
            IP: {"ip": IP, "mac": MAC, "moduleName": "ESP25_SHRGB_01"}
        }
        self.last_pilot: dict[str, dict[str, Any]] = {
            IP: {"mac": MAC, "state": True, "dimming": 50}
        }
        self.query_calls: list[tuple[str, str]] = []

    async def query(self, ip, method, loop, timeout=None, retries=None):
        self.query_calls.append((ip, method))
        if method == "getSystemConfig":
            return {"mac": MAC, "moduleName": "ESP25_SHRGB_01"}
        if method == "getModelConfig":
            return {}
        if method == "getPilot":
            return {"mac": MAC, "state": True, "dimming": 50}
        return None

    def send_pilot(self, ip, params):
        return None


@pytest.fixture()
def controller(tmp_path, monkeypatch):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    import config.paths as app_paths

    monkeypatch.setattr(app_paths, "_INITIALIZED_DIRS", set())
    item = LightController()
    item.proto = FakeProto()
    item.bulb_ips = {IP}
    item.bulbs = {
        IP: {
            "ip": IP,
            "mac": MAC,
            "state": {"mac": MAC, "state": True, "dimming": 50},
            "caps": None,
            "name": "Test",
        }
    }
    item._active_ip = IP
    item.bulbs_manager.add_bulb({"ip": IP, "mac": MAC, "port": 38899})
    yield item
    try:
        item.loop.close()
    except Exception:
        pass


def test_remove_active_bulb_purges_all_caches_and_persists_tombstone(controller):
    controller.remove_bulb(IP)

    assert IP not in controller.bulb_ips
    assert IP not in controller.bulbs
    assert IP not in controller.proto.discovered
    assert IP not in controller.proto.last_pilot
    assert IP not in controller.bulbs_manager.get_bulbs()
    assert controller.get_target_config()["active_ip"] is None
    assert controller.get_target_config()["targets"] == []
    assert controller.get_bulbs_detailed() == []
    assert controller._is_removed_bulb(IP, MAC) is True

    persisted = controller.config.get("removed_bulbs", [])
    assert any(
        item.get("ip") == IP and item.get("mac") == MAC
        for item in persisted
        if isinstance(item, dict)
    )


def test_late_getpilot_cannot_resurrect_removed_bulb(controller):
    controller.remove_bulb(IP)

    changed = controller._merge_pilot_state(
        IP,
        {"mac": MAC, "state": True, "dimming": 75, "r": 255, "g": 0, "b": 0},
    )

    assert changed is False
    assert IP not in controller.bulb_ips
    assert IP not in controller.bulbs
    assert IP not in controller.proto.discovered
    assert controller.get_bulbs_detailed() == []


def test_late_probe_cannot_resurrect_removed_bulb(controller):
    controller.remove_bulb(IP)

    result = asyncio.run(controller._probe(IP))

    assert result is False
    assert controller.proto.query_calls == []
    assert IP not in controller.bulb_ips
    assert IP not in controller.bulbs_manager.get_bulbs()


def test_stale_protocol_cache_is_pruned_from_public_device_list(controller):
    controller.remove_bulb(IP)
    controller.proto.discovered[IP] = {"ip": IP, "mac": MAC}
    controller.proto.last_pilot[IP] = {"mac": MAC, "state": True}

    assert controller.get_bulbs_detailed() == []
    assert IP not in controller.proto.discovered
    assert IP not in controller.proto.last_pilot
    assert controller.get_target_config()["targets"] == []


def test_explicit_rescan_allows_removed_bulb_to_be_found_again(controller):
    controller.remove_bulb(IP)
    assert controller._is_removed_bulb(IP, MAC) is True

    def discard(coroutine):
        coroutine.close()
        return None

    controller._run_coro = discard
    controller.rescan()

    assert controller._is_removed_bulb(IP, MAC) is False
