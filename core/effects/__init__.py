"""Modelos y utilidades puras para efectos dinámicos."""

from .models import (
    DeviceCapabilities,
    EffectFrame,
    RGBColor,
    RGBICFrame,
    RGBICZone,
)
from .rgbic_simulator import SimulatedRGBICZone, simulate_rgbic

__all__ = [
    "DeviceCapabilities",
    "EffectFrame",
    "RGBColor",
    "RGBICFrame",
    "RGBICZone",
    "SimulatedRGBICZone",
    "simulate_rgbic",
]
