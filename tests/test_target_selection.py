from core.light_controller import LightController


def _controller_for_targets(mode, selected, reachable):
    controller = LightController.__new__(LightController)
    controller._target_mode = mode
    controller._selected_ips = set(selected)
    controller._reachable_targets = lambda: set(reachable)
    controller._saved_targets = lambda: set(reachable)
    controller._ensure_active_ip = lambda: "192.168.1.10"
    return controller


def test_selected_mode_targets_only_requested_lights():
    controller = _controller_for_targets(
        "selected",
        {"192.168.1.10", "192.168.1.12"},
        {"192.168.1.10", "192.168.1.11", "192.168.1.12"},
    )

    assert controller._control_targets() == {
        "192.168.1.10",
        "192.168.1.12",
    }


def test_all_mode_keeps_all_reachable_lights():
    controller = _controller_for_targets(
        "all",
        {"192.168.1.10"},
        {"192.168.1.10", "192.168.1.11", "192.168.1.12"},
    )

    assert controller._control_targets() == {
        "192.168.1.10",
        "192.168.1.11",
        "192.168.1.12",
    }


def test_single_mode_keeps_only_active_light():
    controller = _controller_for_targets(
        "single",
        {"192.168.1.10", "192.168.1.12"},
        {"192.168.1.10", "192.168.1.11", "192.168.1.12"},
    )

    assert controller._control_targets() == {"192.168.1.10"}
