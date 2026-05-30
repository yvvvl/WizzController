"""Capacidades WiZ a partir de moduleName/getModelConfig/getPilot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Capabilities:
    rgb: bool = False
    tunable_white: bool = False
    dimmable: bool = True
    on_off: bool = True
    ratio: bool = False
    fan: bool = False
    power_meter: bool = False
    kelvin_min: int = 2700
    kelvin_max: int = 6500
    model: str | None = None

    @property
    def label(self) -> str:
        extra = " + Ratio" if self.ratio else ""
        if self.fan:
            return "Ventilador"
        if self.rgb:
            return "RGB + Blancos" + extra
        if self.tunable_white:
            return "Blancos" + extra
        if self.dimmable:
            return "Regulable" + extra
        return "On/Off"


def _kelvin_range_from_dict(data: dict[str, Any] | None) -> tuple[int, int] | None:
    if not isinstance(data, dict):
        return None

    for key in ("cctRange", "extRange", "whiteRange"):
        raw = data.get(key)
        if isinstance(raw, (list, tuple)):
            vals = []
            for item in raw:
                try:
                    value = int(float(item))
                except (TypeError, ValueError):
                    continue
                if 1000 <= value <= 10000:
                    vals.append(value)
            if vals:
                return min(vals), max(vals)

    lo = data.get("temperatureMin") or data.get("tempMin")
    hi = data.get("temperatureMax") or data.get("tempMax")
    try:
        if lo and hi:
            return int(lo), int(hi)
    except (TypeError, ValueError):
        return None

    return None


def from_module_name(module_name: str | None) -> Capabilities:
    n = (module_name or "").upper()
    caps = Capabilities(model=module_name)

    if "SOCKET" in n or "PLUG" in n:
        caps.dimmable = False
        return caps

    if "FAN" in n:
        caps.fan = True
        return caps

    if "RGB" in n or "SHRGB" in n or "RGBTW" in n:
        caps.rgb = True
        caps.tunable_white = True
        caps.dimmable = True
        caps.kelvin_min, caps.kelvin_max = 2200, 6500
    elif "TW" in n:
        caps.tunable_white = True
        caps.dimmable = True
        caps.kelvin_min, caps.kelvin_max = 2700, 6500
    elif "DW" in n or "DIM" in n:
        caps.dimmable = True
        caps.tunable_white = False
    elif n:
        # Fallback conservador: muchas WiZ viejas no reportan bien moduleName.
        caps.tunable_white = True

    return caps


def from_wiz_config(
    system_config: dict[str, Any] | None,
    model_config: dict[str, Any] | None = None,
    pilot: dict[str, Any] | None = None,
) -> Capabilities:
    module = (system_config or {}).get("moduleName")
    caps = from_module_name(module)

    if isinstance(model_config, dict):
        kr = _kelvin_range_from_dict(model_config)
        if kr:
            caps.kelvin_min, caps.kelvin_max = kr
            caps.tunable_white = True
        if model_config.get("hasRatio") or model_config.get("ratio"):
            caps.ratio = True
        if model_config.get("fanSpeedSteps") or model_config.get("fanSpeed"):
            caps.fan = True

    if isinstance(pilot, dict):
        if all(k in pilot for k in ("r", "g", "b")):
            caps.rgb = True
            caps.tunable_white = True
        if "temp" in pilot or "cctRange" in pilot:
            caps.tunable_white = True
        if "ratio" in pilot:
            caps.ratio = True
        if "pc" in pilot or "power" in pilot:
            caps.power_meter = True
        kr = _kelvin_range_from_dict(pilot)
        if kr:
            caps.kelvin_min, caps.kelvin_max = kr

    return caps
