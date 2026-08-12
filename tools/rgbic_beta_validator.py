from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from core.effects.models import CalibrationProfile, RGBColor, RGBICFrame, RGBICProgram
from core.effects.rgbic_mapper import (
    MAX_RGBIC_PHYSICAL_STEPS,
    compress_rgbic_colors,
    map_rgbic_frame,
)
from core.light_controller import LightController

ARTIFACTS_DIR = Path("artifacts") / "rgbic-validation"
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAC_PATTERN = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")


def sanitize_validation_record(record: dict[str, Any]) -> dict[str, Any]:
    """Redacta identificadores sensibles antes de persistir artefactos locales."""
    payload = json.loads(json.dumps(record))
    _sanitize_inplace(payload)
    return payload


def _sanitize_inplace(value: Any) -> Any:
    if isinstance(value, dict):
        for key, item in list(value.items()):
            if key.lower() == "mac":
                value[key] = "<redacted>"
            elif key.lower() == "ip":
                value[key] = "<redacted>"
            else:
                value[key] = _sanitize_inplace(item)
        return value
    if isinstance(value, list):
        return [_sanitize_inplace(item) for item in value]
    if isinstance(value, str):
        return MAC_PATTERN.sub("<redacted>", IP_PATTERN.sub("<redacted>", value))
    return value


def build_logical_colors(pattern: str, logical_regions: int) -> tuple[RGBColor, ...]:
    if logical_regions < 1:
        raise ValueError("logical_regions must be positive")
    if pattern == "red_blue_split":
        midpoint = max(1, logical_regions // 2)
        return tuple(
            RGBColor(255, 0, 0) if index < midpoint else RGBColor(0, 0, 255)
            for index in range(logical_regions)
        )
    if pattern == "rgb_repeat":
        palette = (RGBColor(255, 0, 0), RGBColor(0, 255, 0), RGBColor(0, 0, 255))
        return tuple(palette[index % len(palette)] for index in range(logical_regions))
    if pattern == "uniform_coverage":
        return tuple(RGBColor(255, 255, 255) for _ in range(logical_regions))
    if pattern == "twelve_step_test":
        palette = (
            RGBColor(255, 0, 0),
            RGBColor(255, 127, 0),
            RGBColor(255, 255, 0),
            RGBColor(0, 255, 0),
            RGBColor(0, 255, 255),
            RGBColor(0, 0, 255),
            RGBColor(127, 0, 255),
            RGBColor(255, 0, 255),
            RGBColor(255, 0, 127),
            RGBColor(255, 255, 255),
            RGBColor(127, 127, 127),
            RGBColor(0, 0, 0),
        )
        return tuple(palette[index % len(palette)] for index in range(logical_regions))
    if pattern == "rainbow_gradient":
        if logical_regions == 1:
            return (RGBColor(255, 0, 0),)
        return tuple(
            RGBColor(
                round(255 * index / (logical_regions - 1)),
                0,
                round(255 * (logical_regions - 1 - index) / (logical_regions - 1)),
            )
            for index in range(logical_regions)
        )
    raise ValueError(f"Unsupported pattern: {pattern}")


def prepare_rgbic_program(
    pattern: str,
    *,
    logical_regions: int,
    physical_segments: int,
    modifier: int,
    support: int,
    brightness: int | None = None,
) -> RGBICProgram:
    logical_colors = build_logical_colors(pattern, logical_regions)
    compressed = compress_rgbic_colors(
        logical_colors,
        max_steps=MAX_RGBIC_PHYSICAL_STEPS,
    )
    steps = map_rgbic_frame(
        RGBICFrame(colors=compressed),
        CalibrationProfile(physical_segments=physical_segments),
        brightness=brightness,
    )
    return RGBICProgram(steps=steps, modifier=modifier, support=support)


def save_validation_record(record: dict[str, Any]) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    sanitized = sanitize_validation_record(record)
    filename = f"{sanitized['timestamp'].replace(':', '').replace('-', '')}.json"
    destination = ARTIFACTS_DIR / filename
    destination.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
    return destination


def main() -> int:
    controller = LightController()
    controller.start()
    try:
        physical_segments = int(input("physical_segments: ").strip())
        scene_id = int(input("sceneId: ").strip())
        pattern = input(
            "pattern [red_blue_split|rgb_repeat|rainbow_gradient|uniform_coverage|twelve_step_test]: "
        ).strip()
        program = prepare_rgbic_program(
            pattern,
            logical_regions=max(physical_segments, MAX_RGBIC_PHYSICAL_STEPS),
            physical_segments=physical_segments,
            modifier=100,
            support=physical_segments,
            brightness=100,
        )
        results = controller.send_rgbic_program(program, scene_id=scene_id)
        visual = input("visual_status [unconfirmed|confirmed_correct|confirmed_wrong]: ").strip() or "unconfirmed"
        notes = input("notes: ").strip()
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "moduleName": None,
            "fwVersion": None,
            "physicalSegments": physical_segments,
            "maxPhysicalSteps": MAX_RGBIC_PHYSICAL_STEPS,
            "sceneId": scene_id,
            "modifier": program.modifier,
            "support": program.support,
            "payload": {
                "state": True,
                "sceneId": scene_id,
                "elm": {
                    "modifier": program.modifier,
                    "support": program.support,
                    "steps": [
                        [0, step.color.red, step.color.green, step.color.blue, 0, 0, 0, step.brightness or 100, 0, 0, 0, 0, step.width]
                        for step in program.steps
                    ],
                },
            },
            "transport_status": results[0].transport_status if results else "error",
            "transport_error": results[0].transport_error if results else {"message": "No targets"},
            "visual_status": visual,
            "notes": notes,
        }
        destination = save_validation_record(record)
        print(f"Saved validation artifact to {destination}")
        return 0
    finally:
        try:
            controller.stop()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
