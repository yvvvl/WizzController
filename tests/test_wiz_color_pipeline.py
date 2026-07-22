from __future__ import annotations

from core.light_controller import LightController
from core.wiz_color import (
    display_rgb_to_wiz_channels,
    logical_rgb_from_state,
    wiz_channels_to_display_rgb,
)


def test_pastel_coral_uses_warm_white_channel() -> None:
    # This is the colour from the real-world report.
    assert display_rgb_to_wiz_channels((255, 173, 158)) == {
        "r": 180,
        "g": 27,
        "b": 0,
        "w": 128,
    }


def test_saturated_primaries_stay_rgb_only() -> None:
    assert display_rgb_to_wiz_channels((255, 0, 0)) == {"r": 255, "g": 0, "b": 0, "w": 0}
    assert display_rgb_to_wiz_channels((0, 255, 0)) == {"r": 0, "g": 255, "b": 0, "w": 0}
    assert display_rgb_to_wiz_channels((0, 0, 255)) == {"r": 0, "g": 0, "b": 255, "w": 0}


def test_display_white_uses_white_emitter() -> None:
    assert display_rgb_to_wiz_channels((255, 255, 255)) == {"r": 0, "g": 0, "b": 0, "w": 128}


def test_inverse_mapping_is_close_for_external_state() -> None:
    result = wiz_channels_to_display_rgb(180, 27, 0, warm_white=128)
    expected = (255, 173, 158)
    assert all(abs(a - b) <= 3 for a, b in zip(result, expected))


def _bare_controller() -> LightController:
    controller = LightController.__new__(LightController)
    controller._target = {}
    controller._mirror = {}
    controller._dirty = False
    controller._logical_rgb = None
    controller._logical_rgb_device = None
    return controller


def test_controller_sends_rgbtw_but_exposes_requested_srgb() -> None:
    controller = _bare_controller()
    controller.set_rgb(255, 173, 158)

    assert controller._target == {
        "state": True,
        "r": 180,
        "g": 27,
        "b": 0,
        "w": 128,
    }
    state = controller.get_state()
    assert (state["r"], state["g"], state["b"]) == (255, 173, 158)
    assert state["device_color"] == {"r": 180, "g": 27, "b": 0, "c": 0, "w": 128}


def test_external_rgbtw_state_is_normalized_for_ui() -> None:
    state = {"state": True, "dimming": 100, "r": 180, "g": 27, "b": 0, "w": 128}
    logical = logical_rgb_from_state(state)
    assert logical is not None
    assert all(abs(a - b) <= 3 for a, b in zip(logical, (255, 173, 158)))
