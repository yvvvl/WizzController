"""Representacion pura y verificable de segmentos RGBIC, sin hardware."""
from __future__ import annotations

from dataclasses import dataclass

from .models import CalibrationProfile, RGBColor, RGBICStep

BLACK = RGBColor(0, 0, 0)


@dataclass(frozen=True, slots=True)
class SimulatedRGBICSegment:
    """Un segmento fisico visible de la simulacion RGBIC."""

    number: int
    step_number: int | None
    color: RGBColor
    brightness: int | None
    padded: bool


def simulate_rgbic(
    steps: tuple[RGBICStep, ...] | list[RGBICStep],
    calibration: CalibrationProfile,
) -> tuple[SimulatedRGBICSegment, ...]:
    """Expande steps secuenciales sobre una cantidad fisica de segmentos."""
    try:
        normalized_steps = tuple(steps)
    except TypeError as exc:
        raise ValueError("steps must be an iterable of RGBICStep") from exc
    if any(not isinstance(step, RGBICStep) for step in normalized_steps):
        raise ValueError("steps must contain only RGBICStep values")
    if not isinstance(calibration, CalibrationProfile):
        raise ValueError("calibration must be a CalibrationProfile")

    total_width = sum(step.width for step in normalized_steps)
    if total_width > calibration.physical_segments:
        raise ValueError("total RGBIC step width cannot exceed physical_segments")

    represented: list[SimulatedRGBICSegment] = []
    next_segment = 1

    for step_number, step in enumerate(normalized_steps, start=1):
        for _ in range(step.width):
            represented.append(
                SimulatedRGBICSegment(
                    number=next_segment,
                    step_number=step_number,
                    color=step.color,
                    brightness=step.brightness,
                    padded=False,
                )
            )
            next_segment += 1

    while next_segment <= calibration.physical_segments:
        represented.append(
            SimulatedRGBICSegment(
                number=next_segment,
                step_number=None,
                color=BLACK,
                brightness=None,
                padded=True,
            )
        )
        next_segment += 1

    return tuple(represented)
