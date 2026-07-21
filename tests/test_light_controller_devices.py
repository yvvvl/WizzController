from __future__ import annotations

from types import SimpleNamespace

from core import light_controller as light_module
from core.light_controller import LightController


IP = "192.168.1.44"
MAC = "aa:bb:cc:dd:ee:ff"


def _controller(monkeypatch, config_dir):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(config_dir))
    controller = LightController()
    controller.proto = SimpleNamespace(discovered={}, last_pilot={})
    return controller


def _close(controller: LightController) -> None:
    if not controller.loop.is_closed():
        controller.loop.close()


def test_remove_bulb_clears_runtime_caches_and_persists_tombstone(monkeypatch, tmp_path):
    controller = _controller(monkeypatch, tmp_path)
    try:
        controller.bulb_ips.add(IP)
        controller.bulbs[IP] = {"ip": IP, "mac": MAC, "state": {"state": True}}
        controller.bulbs_manager.add_bulb({"ip": IP, "mac": MAC, "port": 38899})
        controller.proto.discovered[IP] = {"ip": IP, "mac": MAC}
        controller.proto.last_pilot[IP] = {"state": True, "mac": MAC}
        controller._last_state_signature[IP] = (("state", True),)
        controller._active_ip = IP

        assert controller.remove_bulb(IP) is True
        assert IP not in controller.bulb_ips
        assert IP not in controller.bulbs
        assert IP not in controller.proto.discovered
        assert IP not in controller.proto.last_pilot
        assert IP not in controller._last_state_signature
        assert IP not in controller.bulbs_manager.get_bulbs()
        assert controller.get_bulbs_detailed() == []
        assert controller._is_removed_bulb(IP, MAC) is True
        assert controller.config.get("removed_bulbs")
    finally:
        _close(controller)


def test_removed_bulb_stays_hidden_after_restart_even_if_ip_changes(monkeypatch, tmp_path):
    first = _controller(monkeypatch, tmp_path)
    try:
        first.bulb_ips.add(IP)
        first.bulbs_manager.add_bulb({"ip": IP, "mac": MAC, "port": 38899})
        assert first.remove_bulb(IP) is True
    finally:
        _close(first)

    second = _controller(monkeypatch, tmp_path)
    moved_ip = "192.168.1.99"
    try:
        second.proto.discovered[moved_ip] = {"ip": moved_ip, "mac": MAC}
        assert second._is_removed_bulb(moved_ip, MAC) is True
        assert moved_ip not in second._reachable_targets()

        # Una búsqueda explícita vuelve a admitir dispositivos quitados.
        assert second._clear_removed_bulbs() is True
        assert moved_ip in second._reachable_targets()
    finally:
        _close(second)


def test_discovery_failure_always_releases_scanning_state(monkeypatch, tmp_path):
    controller = _controller(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(
            light_module,
            "get_broadcast_addresses",
            lambda: (_ for _ in ()).throw(RuntimeError("red no disponible")),
        )
        assert controller._claim_scan(explicit=False) is True
        result = controller.loop.run_until_complete(
            controller._discover(aggressive=True, scan_claimed=True)
        )
        status = controller.get_scan_status()

        assert result is False
        assert status["running"] is False
        assert "red no disponible" in str(status["error"])
        assert status["finished_at"] >= status["started_at"]
    finally:
        _close(controller)


def test_duplicate_rescan_is_rejected_instead_of_queued(monkeypatch, tmp_path):
    controller = _controller(monkeypatch, tmp_path)
    try:
        assert controller._claim_scan(explicit=False) is True
        assert controller.rescan() is False
        assert controller.get_scan_status()["running"] is True
        controller._finish_scan()
        assert controller.get_scan_status()["running"] is False
    finally:
        _close(controller)
