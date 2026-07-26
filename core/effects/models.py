"""Modelos inmutables e independientes del transporte para efectos dinámicos."""
from __future__ import annotations

import math
from dataclasses import dataclass

MAX_RGBIC_ZONES = 12


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
    """Muestra temporal de colores destinada a un target lógico."""

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
            if any(
                type(zone) is not int or zone < 1 or zone > MAX_RGBIC_ZONES
                for zone in normalized_zones
            ):
                raise ValueError(
                    f"zone ids must be between 1 and {MAX_RGBIC_ZONES}"
                )
            if len(set(normalized_zones)) != len(normalized_zones):
                raise ValueError("zone ids must be unique")

        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "target", self.target.strip())
        object.__setattr__(self, "colors", colors)
        object.__setattr__(self, "zones", normalized_zones)


@dataclass(frozen=True, slots=True)
class RGBICZone:
    """Color de una zona y su peso/ancho relativo opcional."""

    color: RGBColor
    weight: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.color, RGBColor):
            raise ValueError("color must be an RGBColor")
        if self.weight is not None and (
            isinstance(self.weight, bool)
            or not isinstance(self.weight, (int, float))
            or not math.isfinite(self.weight)
            or self.weight <= 0
        ):
            raise ValueError("weight must be a positive finite number")


@dataclass(frozen=True, slots=True)
class RGBICFrame:
    """Frame lógico de hasta doce zonas RGBIC."""

    zones: tuple[RGBICZone, ...]

    def __post_init__(self) -> None:
        try:
            zones = tuple(self.zones)
        except TypeError as exc:
            raise ValueError("zones must be an iterable of RGBICZone") from exc
        if len(zones) > MAX_RGBIC_ZONES:
            raise ValueError(
                f"an RGBIC frame supports at most {MAX_RGBIC_ZONES} zones"
            )
        if any(not isinstance(zone, RGBICZone) for zone in zones):
            raise ValueError("zones must contain only RGBICZone values")
        object.__setattr__(self, "zones", zones)


@dataclass(frozen=True, slots=True)
class DeviceCapabilities:
    """Capacidades declarativas preparadas para dispositivos futuros."""

    rgb: bool = False
    white: bool = False
    scenes: bool = False
    rgbic_zones: int | None = None

    def __post_init__(self) -> None:
        if self.rgbic_zones is not None and (
            type(self.rgbic_zones) is not int
            or self.rgbic_zones < 1
            or self.rgbic_zones > MAX_RGBIC_ZONES
        ):
            raise ValueError(
                f"rgbic_zones must be between 1 and {MAX_RGBIC_ZONES}"
            )
