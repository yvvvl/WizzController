"""Modelos inmutables e independientes del transporte para efectos dinamicos."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

MAX_RGBIC_PHYSICAL_STEPS = 12

TransportStatus = Literal["sent", "accepted", "rejected", "timeout", "error"]
VisualStatus = Literal["unconfirmed", "confirmed_correct", "confirmed_wrong"]


@dataclass(frozen=True, slots=True)
class RGBColor:
    """Color RGB con canales de ocho bits."""

    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        channels = (self.red, self.green, self.blue)
        if any(type(channel) is not int for channel in channels):
            raise ValueError("RGB channels must be integers")
        if any(channel < 0 or channel > 255 for channel in channels):
            raise ValueError("RGB channels must be between 0 and 255")


@dataclass(frozen=True, slots=True)
class EffectFrame:
    """Muestra temporal de colores destinada a un target logico."""

    timestamp: float
    target: str
    colors: tuple[RGBColor, ...]
    zones: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.timestamp, bool):
            raise ValueError("timestamp must be a finite non-negative number")
        try:
            timestamp = float(self.timestamp)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "timestamp must be a finite non-negative number"
            ) from exc
        if not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("timestamp must be a finite non-negative number")

        if not isinstance(self.target, str) or not self.target.strip():
            raise ValueError("target must be a non-empty string")

        try:
            colors = tuple(self.colors)
        except TypeError as exc:
            raise ValueError("colors must be an iterable of RGBColor") from exc
        if any(not isinstance(color, RGBColor) for color in colors):
            raise ValueError("colors must contain only RGBColor values")

        normalized_zones: tuple[int, ...] | None = None
        if self.zones is not None:
            try:
                normalized_zones = tuple(self.zones)
            except TypeError as exc:
                raise ValueError("zones must be an iterable of zone ids") from exc
            if len(normalized_zones) != len(colors):
                raise ValueError("zones and colors must have the same length")
            if any(type(zone) is not int or zone < 1 for zone in normalized_zones):
                raise ValueError("zone ids must be positive integers")
            if len(set(normalized_zones)) != len(normalized_zones):
                raise ValueError("zone ids must be unique")

        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "target", self.target.strip())
        object.__setattr__(self, "colors", colors)
        object.__setattr__(self, "zones", normalized_zones)


@dataclass(frozen=True, slots=True)
class RGBICFrame:
    """Frame logico compresible de colores para mapping RGBIC."""

    colors: tuple[RGBColor, ...]

    def __post_init__(self) -> None:
        try:
            colors = tuple(self.colors)
        except TypeError as exc:
            raise ValueError("colors must be an iterable of RGBColor") from exc
        if any(not isinstance(color, RGBColor) for color in colors):
            raise ValueError("colors must contain only RGBColor values")
        object.__setattr__(self, "colors", colors)


@dataclass(frozen=True, slots=True)
class RGBICStep:
    """Representacion fisica secuencial de un step RGBIC."""

    color: RGBColor
    width: int
    brightness: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.color, RGBColor):
            raise ValueError("color must be an RGBColor")
        if type(self.width) is not int or self.width <= 0:
            raise ValueError("width must be a positive integer")
        if self.brightness is not None and (
            type(self.brightness) is not int
            or self.brightness < 0
            or self.brightness > 100
        ):
            raise ValueError("brightness must be an integer between 0 and 100")


@dataclass(frozen=True, slots=True)
class RGBICProgram:
    """Contenedor fisico completo para elm RGBIC sin datos de transporte."""

    steps: tuple[RGBICStep, ...]
    modifier: int
    support: int

    def __post_init__(self) -> None:
        try:
            steps = tuple(self.steps)
        except TypeError as exc:
            raise ValueError("steps must be an iterable of RGBICStep") from exc
        if len(steps) < 1 or len(steps) > MAX_RGBIC_PHYSICAL_STEPS:
            raise ValueError(
                f"steps must contain between 1 and {MAX_RGBIC_PHYSICAL_STEPS} RGBICStep values"
            )
        if any(not isinstance(step, RGBICStep) for step in steps):
            raise ValueError("steps must contain only RGBICStep values")
        if type(self.modifier) is not int:
            raise ValueError("modifier must be an integer")
        if type(self.support) is not int or self.support <= 0:
            raise ValueError("support must be a positive integer")
        object.__setattr__(self, "steps", steps)


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    """Describe la instalacion fisica necesaria para mapping RGBIC."""

    physical_segments: int

    def __post_init__(self) -> None:
        if type(self.physical_segments) is not int or self.physical_segments <= 0:
            raise ValueError("physical_segments must be a positive integer")


@dataclass(frozen=True, slots=True)
class DeviceCapabilities:
    """Capacidades declarativas preparadas para dispositivos futuros."""

    rgb: bool = False
    white: bool = False
    scenes: bool = False
    rgbic: bool = False
    rgbic_max_steps: int | None = None

    def __post_init__(self) -> None:
        if self.rgbic_max_steps is not None and (
            type(self.rgbic_max_steps) is not int or self.rgbic_max_steps <= 0
        ):
            raise ValueError("rgbic_max_steps must be a positive integer")


@dataclass(frozen=True, slots=True)
class RGBICTransportResult:
    """Resultado experimental del puente RGBIC oficial."""

    target_ip: str
    scene_id: int
    transport_status: TransportStatus
    visual_status: VisualStatus = "unconfirmed"
    transport_error: dict[str, Any] | None = None
