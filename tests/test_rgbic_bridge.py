from __future__ import annotations

from typing import Any

from core.effects.models import RGBColor, RGBICProgram, RGBICStep
from core.light_controller import LightController


IP = "192.0.2.10"


class FakeProto:
    def __init__(self, responses: dict[tuple[str, int], dict[str, Any] | None]) -> None:
        self.responses = responses
        self.query_calls: list[tuple[str, str, dict[str, Any], float, int]] = []

    async def query(self, ip, method, loop=None, timeout=None, params=None, retries=None):
        self.query_calls.append((ip, method, params or {}, timeout or 0.0, retries or 0))
        return self.responses.get((ip, params["sceneId"]))


def _controller_with_proto(proto: FakeProto) -> LightController:
    controller = LightController.__new__(LightController)
    controller.proto = proto
    controller._target_mode = "single"
    controller._active_ip = IP
    controller._state_sync_max_targets = 1
    controller._control_targets = lambda: {IP}
    controller.loop = None
    controller._run_coro = None
    return controller


def test_light_controller_uses_wiz_protocol_for_rgbic_bridge():
    controller = _controller_with_proto(FakeProto({(IP, 258): {"success": True}}))
    result = controller.send_rgbic_program(
        RGBICProgram(
            steps=[RGBICStep(RGBColor(255, 0, 0), width=1)],
            modifier=100,
            support=17,
        ),
        scene_id=258,
    )

    assert len(result) == 1
    assert result[0].transport_status == "accepted"
    assert result[0].visual_status == "unconfirmed"
    assert controller.proto.query_calls[0][1] == "setPilot"
    assert controller.proto.query_calls[0][2]["sceneId"] == 258


def test_rgbic_bridge_keeps_visual_status_unconfirmed_on_success():
    controller = _controller_with_proto(FakeProto({(IP, 258): {"success": True}}))

    result = controller.send_rgbic_program(
        RGBICProgram(
            steps=[RGBICStep(RGBColor(255, 0, 0), width=1)],
            modifier=100,
            support=17,
        ),
        scene_id=258,
    )[0]

    assert result.transport_status == "accepted"
    assert result.visual_status == "unconfirmed"


def test_rgbic_bridge_preserves_wiz_error_payload():
    controller = _controller_with_proto(
        FakeProto(
            {
                (IP, 258): {
                    "error": {"code": -32602, "message": "Invalid params"}
                }
            }
        )
    )

    result = controller.send_rgbic_program(
        RGBICProgram(
            steps=[RGBICStep(RGBColor(255, 0, 0), width=1)],
            modifier=100,
            support=17,
        ),
        scene_id=258,
    )[0]

    assert result.transport_status == "rejected"
    assert result.transport_error == {"code": -32602, "message": "Invalid params"}
    assert result.visual_status == "unconfirmed"


def test_rgbic_bridge_requires_explicit_scene_id():
    controller = _controller_with_proto(FakeProto({}))

    try:
        controller.send_rgbic_program(
            RGBICProgram(
                steps=[RGBICStep(RGBColor(255, 0, 0), width=1)],
                modifier=100,
                support=17,
            ),
            scene_id="258",
        )
    except ValueError as exc:
        assert "scene_id must be an integer" in str(exc)
    else:
        raise AssertionError("scene_id must be explicit and typed as int")
