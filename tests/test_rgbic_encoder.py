from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.effects.models import RGBColor, RGBICProgram, RGBICStep
from core.effects.rgbic_encoder import encode_rgbic_program


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "rgbic"


def test_encoder_builds_exact_setpilot_params_without_mac():
    program = RGBICProgram(
        steps=[
            RGBICStep(RGBColor(0, 255, 0), width=1),
            RGBICStep(RGBColor(0, 0, 255), width=2, brightness=40),
        ],
        modifier=100,
        support=17,
    )

    payload = encode_rgbic_program(program, scene_id=258)

    assert payload == {
        "state": True,
        "sceneId": 258,
        "elm": {
            "modifier": 100,
            "support": 17,
            "steps": [
                [0, 0, 255, 0, 0, 0, 0, 100, 0, 0, 0, 0, 1],
                [0, 0, 0, 255, 0, 0, 0, 40, 0, 0, 0, 0, 2],
            ],
        },
    }
    assert "mac" not in payload


def test_encoder_defaults_missing_step_brightness_to_one_hundred():
    program = RGBICProgram(
        steps=[RGBICStep(RGBColor(255, 0, 0), width=3)],
        modifier=123,
        support=17,
    )

    payload = encode_rgbic_program(program, scene_id=258)

    assert payload["elm"]["steps"] == [
        [0, 255, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 3]
    ]


def test_encoder_rejects_more_than_twelve_steps():
    with pytest.raises(ValueError, match="between 1 and 12"):
        encode_rgbic_program(
            RGBICProgram(
                steps=[RGBICStep(RGBColor(1, 2, 3), width=1)] * 13,
                modifier=100,
                support=17,
            ),
            scene_id=258,
        )


def test_encoder_preserves_scene_id_and_zeroes_unknown_indices():
    program = RGBICProgram(
        steps=[RGBICStep(RGBColor(1, 2, 3), width=1, brightness=77)],
        modifier=100,
        support=17,
    )

    payload = encode_rgbic_program(program, scene_id=257)
    step = payload["elm"]["steps"][0]

    assert payload["sceneId"] == 257
    assert len(step) == 13
    assert step[0] == 0
    assert step[1:4] == [1, 2, 3]
    assert step[4:7] == [0, 0, 0]
    assert step[7] == 77
    assert step[8:12] == [0, 0, 0, 0]
    assert step[12] == 1


def test_real_fixture_records_device_and_step_limit_evidence():
    device = json.loads(
        (FIXTURES / "device-esp25-mhorgb-01-fw-1.38.0.json").read_text(
            encoding="utf-8"
        )
    )
    scene_257 = json.loads(
        (FIXTURES / "scene-257-occupied-success-visually-wrong.json").read_text(
            encoding="utf-8"
        )
    )
    scene_258 = json.loads(
        (FIXTURES / "scene-258-empty-success-visually-correct.json").read_text(
            encoding="utf-8"
        )
    )
    limit = json.loads(
        (FIXTURES / "step-limit-fw-1.38.0.json").read_text(encoding="utf-8")
    )
    coverage = json.loads(
        (FIXTURES / "width-coverage-17-segments.json").read_text(encoding="utf-8")
    )

    assert device["moduleName"] == "ESP25_MHORGB_01"
    assert device["fwVersion"] == "1.38.0"
    assert device["physicalSegments"] == 17
    assert device["getSystemConfig"]["physicalSegmentCountPresent"] is False
    assert scene_257["sceneId"] == 257
    assert scene_257["deviceResponse"]["success"] is True
    assert scene_257["visual"] == "visually_wrong"
    assert scene_258["sceneId"] == 258
    assert scene_258["deviceResponse"]["success"] is True
    assert scene_258["visual"] == "visually_correct"
    assert limit["cases"]["12"]["transport"] == "accepted"
    assert limit["cases"]["13"]["error"]["code"] == -32602
    assert coverage["fullCoverage"]["widths"] == [1, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2]
    assert sum(coverage["fullCoverage"]["widths"]) == 17
