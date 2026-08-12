"""Encoder puro de RGBICProgram a params de setPilot."""
from __future__ import annotations

from .models import RGBICProgram, RGBICStep

DEFAULT_STEP_BRIGHTNESS = 100


def encode_rgbic_program(program: RGBICProgram, scene_id: int) -> dict[str, object]:
    """Convierte un programa RGBIC y un slot a params compatibles con setPilot."""
    if not isinstance(program, RGBICProgram):
        raise ValueError("program must be an RGBICProgram")
    if type(scene_id) is not int:
        raise ValueError("scene_id must be an integer")

    if len(program.steps) < 1 or len(program.steps) > 12:
        raise ValueError("steps must contain between 1 and 12 RGBICStep values")

    return {
        "state": True,
        "sceneId": scene_id,
        "elm": {
            "modifier": program.modifier,
            "support": program.support,
            "steps": [_encode_step(step) for step in program.steps],
        },
    }


def _encode_step(step: RGBICStep) -> list[int]:
    brightness = (
        step.brightness if step.brightness is not None else DEFAULT_STEP_BRIGHTNESS
    )
    return [
        0,
        step.color.red,
        step.color.green,
        step.color.blue,
        0,
        0,
        0,
        brightness,
        0,
        0,
        0,
        0,
        step.width,
    ]
