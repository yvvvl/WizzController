"""Modelos y utilidades puras para efectos dinamicos."""

from .models import (
    CalibrationProfile,
    DeviceCapabilities,
    EffectFrame,
    MAX_RGBIC_PHYSICAL_STEPS,
    RGBColor,
    RGBICFrame,
    RGBICProgram,
    RGBICStep,
    RGBICTransportResult,
)
from .rgbic_encoder import encode_rgbic_program
from .rgbic_mapper import compress_rgbic_colors, map_rgbic_frame
from .rgbic_simulator import SimulatedRGBICSegment, simulate_rgbic

__all__ = [
    "CalibrationProfile",
    "DeviceCapabilities",
    "EffectFrame",
    "MAX_RGBIC_PHYSICAL_STEPS",
    "RGBColor",
    "RGBICFrame",
    "RGBICProgram",
    "RGBICStep",
    "RGBICTransportResult",
    "SimulatedRGBICSegment",
    "compress_rgbic_colors",
    "encode_rgbic_program",
    "map_rgbic_frame",
    "simulate_rgbic",
]
