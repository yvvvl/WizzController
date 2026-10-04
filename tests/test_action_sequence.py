import asyncio

from core.action_sequence import ActionSequenceExecutor
from core.dev_virtual_lights import VirtualLightController
from core.light_controller import LightController
from config.routines_manager import RoutinesManager


class FakeWiz:
    def __init__(self):
        self.calls = []
        self.state = {"dimming": 50}

    def turn_on(self): self.calls.append(("turn_on",))
    def turn_off(self): self.calls.append(("turn_off",))
    def toggle(self): self.calls.append(("toggle",))
    def set_brightness(self, value): self.calls.append(("brightness", int(value))); self.state["dimming"] = int(value)
    def set_rgb(self, r, g, b): self.calls.append(("rgb", int(r), int(g), int(b)))
    def set_white(self, k): self.calls.append(("white", int(k)))
    def set_scene(self, sid, speed=None): self.calls.append(("scene", int(sid), speed))
    def get_state(self): return dict(self.state)


def test_sequence_executes_in_order():
    wiz = FakeWiz()
    ex = ActionSequenceExecutor(wiz)
    ex.execute([
        {"type":"turn_on"},
        {"type":"rgb", "value":"#ff0000"},
        {"type":"brightness", "value":50},
    ], threaded=False)
    assert wiz.calls == [("turn_on",), ("rgb",255,0,0), ("brightness",50)]


def test_brightness_delta_uses_dimming():
    wiz = FakeWiz()
    ex = ActionSequenceExecutor(wiz)
    ex.execute({"type":"brightness_delta", "value":10}, threaded=False)
    assert ("brightness", 60) in wiz.calls


def test_condition_stops_remaining_steps_when_it_does_not_match():
    wiz = FakeWiz()
    wiz.state["state"] = False
    ex = ActionSequenceExecutor(wiz)

    result = ex.execute([
        {"type": "condition", "value": "power_on"},
        {"type": "turn_on"},
    ], threaded=False)

    assert wiz.calls == []
    assert "Detenida por condición" in result


def test_condition_allows_remaining_steps_when_it_matches():
    wiz = FakeWiz()
    wiz.state["state"] = True
    ex = ActionSequenceExecutor(wiz)

    ex.execute([
        {"type": "condition", "value": "power_on"},
        {"type": "brightness", "value": 40},
    ], threaded=False)

    assert wiz.calls == [("brightness", 40)]


def test_targeted_steps_control_only_named_virtual_bulb():
    wiz = VirtualLightController(3)
    ips = sorted(wiz.bulbs)
    first, second, third = ips
    target = "mac:" + wiz._normalise_mac(wiz.bulbs[second]["mac"])
    original_mode = wiz.get_target_config()["mode"]
    original_selected = wiz.get_target_config()["selected_ips"]

    ActionSequenceExecutor(wiz).execute([
        {"type": "turn_off", "target": target},
        {"type": "brightness_delta", "value": -30, "target": target},
    ], threaded=False)

    assert wiz.bulbs[first]["state"]["state"] is True
    assert wiz.bulbs[second]["state"]["state"] is False
    assert wiz.bulbs[second]["state"]["dimming"] == 70
    assert wiz.bulbs[third]["state"]["state"] is True
    assert wiz.get_target_config()["mode"] == original_mode
    assert wiz.get_target_config()["selected_ips"] == original_selected


def test_missing_routine_target_never_falls_back_to_current_selection():
    wiz = VirtualLightController(2)
    result = ActionSequenceExecutor(wiz).execute(
        {"type": "turn_off", "target": "mac:000000000000"}, threaded=False
    )
    assert "Destino no disponible" in result
    assert all(bulb["state"]["state"] for bulb in wiz.bulbs.values())


def test_mixed_current_and_specific_steps_keep_routine_order():
    wiz = VirtualLightController(3)
    wiz.turn_off()
    second = sorted(wiz.bulbs)[1]
    target = "mac:" + wiz._normalise_mac(wiz.bulbs[second]["mac"])

    ActionSequenceExecutor(wiz).execute([
        {"type": "turn_on"},
        {"type": "turn_off", "target": target},
    ], threaded=False)

    assert [wiz.bulbs[ip]["state"]["state"] for ip in sorted(wiz.bulbs)] == [True, False, True]


def test_all_lights_target_overrides_current_selection_without_changing_it():
    wiz = VirtualLightController(3)
    first = sorted(wiz.bulbs)[0]
    wiz.set_active_bulb(first)

    ActionSequenceExecutor(wiz).execute(
        {"type": "turn_off", "target": "all"}, threaded=False
    )

    assert not any(bulb["state"]["state"] for bulb in wiz.bulbs.values())
    assert wiz.get_target_config()["mode"] == "single"
    assert wiz.get_target_config()["active_ip"] == first


def test_routine_step_can_target_two_virtual_bulbs_without_touching_the_third():
    wiz = VirtualLightController(3)
    ips = sorted(wiz.bulbs)
    targets = ["mac:" + wiz._normalise_mac(wiz.bulbs[ip]["mac"]) for ip in (ips[0], ips[2])]
    original_mode = wiz.get_target_config()["mode"]

    ActionSequenceExecutor(wiz).execute(
        {"type": "turn_off", "target": targets}, threaded=False
    )

    assert [wiz.bulbs[ip]["state"]["state"] for ip in ips] == [False, True, False]
    assert wiz.get_target_config()["mode"] == original_mode


def test_multi_target_skips_a_missing_member_without_falling_back():
    wiz = VirtualLightController(3)
    ips = sorted(wiz.bulbs)
    first = "mac:" + wiz._normalise_mac(wiz.bulbs[ips[0]]["mac"])

    ActionSequenceExecutor(wiz).execute(
        {"type": "turn_off", "target": [first, "mac:000000000000"]}, threaded=False
    )

    assert [wiz.bulbs[ip]["state"]["state"] for ip in ips] == [False, True, True]


def test_named_light_group_resolves_current_members_and_missing_group_is_safe(monkeypatch, tmp_path):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    wiz = VirtualLightController(3)
    ips = sorted(wiz.bulbs)
    original_mode = wiz.get_target_config()["mode"]
    members = ["mac:" + wiz._normalise_mac(wiz.bulbs[ip]["mac"]) for ip in (ips[0], ips[2])]
    manager = RoutinesManager()
    group = manager.upsert_light_group("", "Living room", members)
    assert group is not None

    action = {"type": "turn_off", "target": "group:" + group["id"]}
    ActionSequenceExecutor(wiz).execute(action, threaded=False)
    assert [wiz.bulbs[ip]["state"]["state"] for ip in ips] == [False, True, False]
    assert wiz.get_target_config()["mode"] == original_mode

    wiz.turn_on()
    manager.upsert_light_group(group["id"], "Living room", [members[1]])
    ActionSequenceExecutor(wiz).execute(action, threaded=False)
    assert [wiz.bulbs[ip]["state"]["state"] for ip in ips] == [True, True, False]

    wiz.turn_on()
    assert manager.remove_light_group(group["id"])
    result = ActionSequenceExecutor(wiz).execute(action, threaded=False)
    assert "Destino no disponible" in result
    assert all(wiz.bulbs[ip]["state"]["state"] for ip in ips)


def test_routine_normalization_keeps_explicit_target_only_for_light_steps():
    manager = RoutinesManager()
    actions = manager.normalize_actions([
        {"type": "turn_off", "target": "mac:020000000001"},
        {"type": "wait", "value": 100, "target": "all"},
    ])
    assert actions == [
        {"type": "turn_off", "target": "mac:020000000001"},
        {"type": "wait", "value": 100},
    ]
    assert manager.normalize_actions([
        {"type": "turn_off", "target": ["mac:020000000001", "mac:020000000002", "mac:020000000001", "all"]},
        {"type": "turn_on", "target": "group:some-id"},
    ]) == [
        {"type": "turn_off", "target": ["mac:020000000001", "mac:020000000002"]},
        {"type": "turn_on", "target": "group:some-id"},
    ]


def test_targeted_routine_keeps_order_with_prior_normal_command():
    wiz = LightController()
    first, second = "192.0.2.20", "192.0.2.21"
    wiz.bulbs = {
        first: {"mac": "02:00:00:00:00:20", "state": {"state": False}},
        second: {"mac": "02:00:00:00:00:21", "state": {"state": False}},
    }
    wiz.bulb_ips = {first, second}
    wiz._active_ip = first
    wiz._target_mode = "all"
    wiz._removed_bulbs = []
    wiz.turn_on()

    ActionSequenceExecutor(wiz).execute(
        {"type": "turn_off", "target": "mac:020000000021"}, threaded=False
    )

    batches = list(wiz._targeted_actions)
    assert len(batches) == 2
    assert {ip for ip, _ in batches[0]} == {first, second}
    assert all(params == {"state": True} for _, params in batches[0])
    assert batches[1] == [(second, {"state": False})]
    assert wiz._dirty is False

    class RecordingProtocol:
        discovered = {}
        last_pilot = {}

        def __init__(self):
            self.calls = []

        def send_pilot(self, ip, params):
            self.calls.append((ip, dict(params)))
            if len(self.calls) == 3:
                wiz.running = False

    protocol = RecordingProtocol()
    wiz.proto = protocol
    wiz.MIN_INTERVAL = 0
    asyncio.run(wiz._pump())
    assert protocol.calls == [
        (first, {"state": True}),
        (second, {"state": True}),
        (second, {"state": False}),
    ]
