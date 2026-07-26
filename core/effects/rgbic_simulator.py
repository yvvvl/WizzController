"""Representación pura y verificable de frames RGBIC, sin hardware."""
from __future__ import annotations

from dataclasses import dataclass

from .models import MAX_RGBIC_ZONES, RGBColor, RGBICFrame

BLACK = RGBColor(0, 0, 0)


@dataclass(frozen=True, slots=True)
class SimulatedRGBICZone:
    """Una posición visible del frame simulado."""

    number: int
    color: RGBColor
    weight: float | None
    padded: bool


def simulate_rgbic(
    frame: RGBICFrame,
) -> tuple[SimulatedRGBICZone, ...]:
    """Expande un frame a doce posiciones, completando con negro."""
    if not isinstance(frame, RGBICFrame):
        raise ValueError("frame must be an RGBICFrame")

    represented = [
        SimulatedRGBICZone(
            number=index,
            color=zone.color,
            weight=zone.weight,
            padded=False,
        )
        for index, zone in enumerate(frame.zones, start=1)
    ]
    represented.extend(
        SimulatedRGBICZone(
            number=index,
            color=BLACK,
            weight=None,
            padded=True,
        )
        for index in range(len(represented) + 1, MAX_RGBIC_ZONES + 1)
    )
    return tuple(represented)
