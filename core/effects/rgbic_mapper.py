"""Mapper puro entre una representacion logica y steps RGBIC fisicos."""
from __future__ import annotations

import math
from collections.abc import Iterable

from .models import (
    CalibrationProfile,
    MAX_RGBIC_PHYSICAL_STEPS,
    RGBColor,
    RGBICFrame,
    RGBICStep,
)


def compress_rgbic_colors(
    colors: Iterable[RGBColor],
    max_steps: int = MAX_RGBIC_PHYSICAL_STEPS,
) -> tuple[RGBColor, ...]:
    """Reduce colores logicos contiguos a un maximo fisico determinista."""
    try:
        normalized = tuple(colors)
    except TypeError as exc:
        raise ValueError("colors must be an iterable of RGBColor") from exc
    if any(not isinstance(color, RGBColor) for color in normalized):
        raise ValueError("colors must contain only RGBColor values")
    if type(max_steps) is not int or max_steps <= 0:
        raise ValueError("max_steps must be a positive integer")
    if len(normalized) <= max_steps:
        return normalized

    color_count = len(normalized)
    compressed: list[RGBColor] = []
    for index in range(max_steps):
        start = math.floor(index * color_count / max_steps)
        end = math.floor((index + 1) * color_count / max_steps)
        group = normalized[start:end]
        compressed.append(
            RGBColor(
                round(sum(color.red for color in group) / len(group)),
                round(sum(color.green for color in group) / len(group)),
                round(sum(color.blue for color in group) / len(group)),
            )
        )
    return tuple(compressed)


def map_rgbic_frame(
    frame: RGBICFrame,
    calibration: CalibrationProfile,
    *,
    brightness: int | None = None,
) -> tuple[RGBICStep, ...]:
    """Distribuye un frame logico sobre la calibracion fisica disponible."""
    if not isinstance(frame, RGBICFrame):
        raise ValueError("frame must be an RGBICFrame")
    if not isinstance(calibration, CalibrationProfile):
        raise ValueError("calibration must be a CalibrationProfile")
    if brightness is not None and (
        type(brightness) is not int or brightness < 0 or brightness > 100
    ):
        raise ValueError("brightness must be an integer between 0 and 100")

    color_count = len(frame.colors)
    if color_count == 0:
        return ()
    if calibration.physical_segments < color_count:
        raise ValueError(
            "physical_segments must be at least the logical color count"
        )

    segment_count = calibration.physical_segments
    return tuple(
        RGBICStep(
            color=color,
            width=(
                math.floor((index + 1) * segment_count / color_count)
                - math.floor(index * segment_count / color_count)
            ),
            brightness=brightness,
        )
        for index, color in enumerate(frame.colors)
    )
