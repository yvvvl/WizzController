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
    fw_version: str | None = None
    type_id: str | int | None = None

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

    def as_dict(self) -> dict[str, Any]:
        return {
            "rgb": self.rgb,
            "tunable_white": self.tunable_white,
            "dimmable": self.dimmable,
            "on_off": self.on_off,
            "ratio": self.ratio,
            "fan": self.fan,
            "power_meter": self.power_meter,
            "kelvin_min": self.kelvin_min,
            "kelvin_max": self.kelvin_max,
            "model": self.model,
            "fw_version": self.fw_version,
            "type_id": self.type_id,
            "label": self.label,
        }


def _int_or_none(value: Any) -> int | None:
    try:
        iv = int(float(value))
    except (TypeError, ValueError):
        return None
    return iv


def _kelvin_range_from_dict(data: dict[str, Any] | None) -> tuple[int, int] | None:
    if not isinstance(data, dict):
        return None

    for key in ("cctRange", "extRange", "whiteRange"):
        raw = data.get(key)
        if isinstance(raw, (list, tuple)):
            vals: list[int] = []
            for item in raw:
                value = _int_or_none(item)
                if value is not None and 1000 <= value <= 10000:
                    vals.append(value)
            if vals:
                return min(vals), max(vals)

    pairs = (
        ("temperatureMin", "temperatureMax"),
        ("tempMin", "tempMax"),
        ("minTemp", "maxTemp"),
    )
    for lo_key, hi_key in pairs:
        lo = _int_or_none(data.get(lo_key))
        hi = _int_or_none(data.get(hi_key))
        if lo and hi and 1000 <= lo <= hi <= 10000:
            return lo, hi

    return None


def from_module_name(module_name: str | None) -> Capabilities:
    n = (module_name or "").upper()
    caps = Capabilities(model=module_name)

    if "SOCKET" in n or "PLUG" in n:
        caps.dimmable = False
        caps.tunable_white = False
        caps.rgb = False
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
        # Muchas WiZ antiguas reportan moduleName incompleto.
        caps.tunable_white = True

    return caps


def from_wiz_config(
    system_config: dict[str, Any] | None,
    model_config: dict[str, Any] | None = None,
    pilot: dict[str, Any] | None = None,
) -> Capabilities:
    system_config = system_config or {}
    model_config = model_config or {}
    pilot = pilot or {}

    module = system_config.get("moduleName") or model_config.get("moduleName")
    caps = from_module_name(module)
    caps.fw_version = system_config.get("fwVersion") or model_config.get("fwVersion")
    caps.type_id = system_config.get("typeId") or model_config.get("typeId")

    kr = _kelvin_range_from_dict(model_config) or _kelvin_range_from_dict(pilot) or _kelvin_range_from_dict(system_config)
    if kr:
        caps.kelvin_min, caps.kelvin_max = kr
        caps.tunable_white = True

    # Señales de canales/capacidades en modelConfig.
    nowc = model_config.get("nowc")
    if nowc is not None:
        try:
            caps.tunable_white = int(nowc) > 0
        except Exception:
            pass
    if model_config.get("wcr") is not None:
        caps.rgb = True
        caps.tunable_white = True
    if model_config.get("hasRatio") or model_config.get("ratio"):
        caps.ratio = True
    if model_config.get("fanSpeedSteps") or model_config.get("fanSpeed"):
        caps.fan = True

    if all(k in pilot for k in ("r", "g", "b")):
        caps.rgb = True
        caps.tunable_white = True
    if "temp" in pilot or "cctRange" in pilot or "whiteRange" in pilot:
        caps.tunable_white = True
    if "ratio" in pilot:
        caps.ratio = True
    if "pc" in pilot or "power" in pilot:
        caps.power_meter = True

    return caps
