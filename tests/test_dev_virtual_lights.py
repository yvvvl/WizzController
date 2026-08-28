from __future__ import annotations

from core.dev_virtual_lights import ENV_NAME, VirtualLightController, virtual_bulb_count_from_environment


def test_virtual_controller_is_in_memory_and_targets_selected_bulbs():
    wiz = VirtualLightController(3)

    assert wiz.proto is None
    assert not wiz.thread.is_alive()
    assert len(wiz.get_bulbs_detailed()) == 3

    wiz.set_target_selection(["192.0.2.10", "192.0.2.12"])
    wiz.set_rgb(255, 0, 0)
    wiz.set_brightness(45)

    bulbs = {item["ip"]: item for item in wiz.get_virtual_bulbs()}
    assert bulbs["192.0.2.10"]["state"]["dimming"] == 45
    assert bulbs["192.0.2.12"]["state"]["dimming"] == 45
    assert bulbs["192.0.2.11"]["state"]["dimming"] == 100


def test_virtual_controller_changes_only_active_bulb_in_single_mode():
    wiz = VirtualLightController(3)
    wiz.set_active_bulb("192.0.2.11")
    wiz.turn_off()

    bulbs = {item["ip"]: item for item in wiz.get_virtual_bulbs()}
    assert bulbs["192.0.2.11"]["state"]["state"] is False
    assert bulbs["192.0.2.10"]["state"]["state"] is True


def test_virtual_bulbs_require_explicit_environment_opt_in(monkeypatch):
    monkeypatch.delenv(ENV_NAME, raising=False)
    assert virtual_bulb_count_from_environment() == 0
    monkeypatch.setenv(ENV_NAME, "99")
    assert virtual_bulb_count_from_environment() == 12


def test_dynamic_scene_has_a_changing_visual_frame_without_network():
    wiz = VirtualLightController(2)
    wiz.set_scene(4, speed=100)

    first = wiz._scene_rgb(4, 1.0)
    later = wiz._scene_rgb(4, 1.6)
    bulbs = wiz.get_virtual_bulbs()

    assert first != later
    assert all(item["state"]["_virtual_rgb"] for item in bulbs)


def test_selecting_another_bulb_does_not_change_an_existing_scene_frame():
    wiz = VirtualLightController(2)
    wiz.set_target_selection(["192.0.2.10"])
    wiz.set_scene(4, speed=180)
    before = wiz.get_virtual_bulbs()[0]["state"]["_virtual_rgb"]

    wiz.set_active_bulb("192.0.2.11")
    after = wiz.get_virtual_bulbs()[0]["state"]["_virtual_rgb"]

    assert before == after


def test_selection_callback_is_marked_so_the_preview_can_preserve_its_colours():
    wiz = VirtualLightController(2)
    snapshots = []
    wiz.set_callback(snapshots.append)

    wiz.set_active_bulb("192.0.2.11")

    assert snapshots[-1]["_virtual_selection_only"] is True
