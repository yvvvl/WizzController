from __future__ import annotations

"""WiZ-aware conversion between display sRGB and RGBTW LED channels.

WiZ colour bulbs expose RGB plus cold/warm-white channels.  A pastel sRGB value
must not be sent directly to only the RGB emitters: on many bulbs that produces a
very different emitted hue.  pywizlight contains the established reverse-
engineered conversion used by its ``PilotBuilder``; this module centralises that
mapping for WizZ Desktop while keeping the UI state in normal sRGB.
"""

import colorsys
from functools import lru_cache
from typing import Any, Iterable

from pywizlight.rgbcw import rgb2rgbcw, rgbcw2hs

RGB = tuple[int, int, int]


def _channel(value: int | float) -> int:
    return max(0, min(255, int(round(float(value)))))


def normalize_rgb(rgb: Iterable[int | float]) -> RGB:
    values = list(rgb)
    if len(values) < 3:
        raise ValueError("RGB requiere tres componentes")
    return _channel(values[0]), _channel(values[1]), _channel(values[2])


def display_rgb_to_wiz_channels(rgb: Iterable[int | float]) -> dict[str, int]:
    """Map a display sRGB colour to WiZ RGBTW pilot channels.

    The returned ``w`` is the warm-white emitter contribution.  ``c`` is kept at
    zero by the caller for RGB mode.  Pure saturated colours remain pure RGB;
    pastel/near-white colours use the white emitter instead of asking the RGB
    LEDs to approximate white.
    """

    logical = normalize_rgb(rgb)
    device_rgb, white = rgb2rgbcw(logical)
    red, green, blue = normalize_rgb(device_rgb)
    return {"r": red, "g": green, "b": blue, "w": _channel(white)}


def wiz_channels_signature(channels: dict[str, Any] | None) -> tuple[int, int, int, int, int]:
    values = channels or {}
    return (
        _channel(values.get("r", 0) or 0),
        _channel(values.get("g", 0) or 0),
        _channel(values.get("b", 0) or 0),
        _channel(values.get("c", values.get("cw", 0)) or 0),
        _channel(values.get("w", values.get("ww", 0)) or 0),
    )


def channel_signatures_close(
    left: tuple[int, int, int, int, int] | None,
    right: tuple[int, int, int, int, int] | None,
    *,
    tolerance: int = 4,
) -> bool:
    if left is None or right is None:
        return False
    tol = max(0, int(tolerance))
    return all(abs(int(a) - int(b)) <= tol for a, b in zip(left, right))


def _device_distance(
    candidate: dict[str, int],
    target: tuple[int, int, int, int, int],
) -> int:
    return (
        abs(candidate["r"] - target[0])
        + abs(candidate["g"] - target[1])
        + abs(candidate["b"] - target[2])
        + abs(candidate["w"] - max(target[3], target[4]))
    )


@lru_cache(maxsize=512)
def _decode_signature_cached(
    signature: tuple[int, int, int, int, int],
) -> RGB:
    """Find the display sRGB whose WiZ mapping best reproduces a device state.

    ``rgbcw2hs`` gives a good analytical starting point, but the forward WiZ
    mapping is quantised and not a simple HSV transform.  A small deterministic
    search around that estimate recovers exact round-trips for colours generated
    by ``rgb2rgbcw`` without doing a 16-million-colour brute force.
    """

    red, green, blue, cold, warm = signature
    white = max(cold, warm)
    if white <= 0 and max(red, green, blue) <= 0:
        return 0, 0, 0

    hue_estimate, saturation_estimate_pct = rgbcw2hs((red, green, blue), white)
    target = signature

    best_distance = 10**9
    best_hue = float(hue_estimate) % 360.0
    best_saturation_step = max(0, min(255, round(float(saturation_estimate_pct) * 2.55)))
    best_rgb: RGB = normalize_rgb((red, green, blue))

    # First solve saturation at the analytical hue.
    for saturation_step in range(256):
        saturation = saturation_step / 255.0
        channels = colorsys.hsv_to_rgb(best_hue / 360.0, saturation, 1.0)
        logical = normalize_rgb(channel * 255.0 for channel in channels)
        mapped = display_rgb_to_wiz_channels(logical)
        distance = _device_distance(mapped, target)
        if distance < best_distance:
            best_distance = distance
            best_saturation_step = saturation_step
            best_rgb = logical

    # Then refine hue in tenths of a degree and saturation near the best step.
    hue_origin = best_hue
    for hue_offset_tenths in range(-120, 121):
        hue = (hue_origin + hue_offset_tenths / 10.0) % 360.0
        for saturation_step in range(
            max(0, best_saturation_step - 5),
            min(255, best_saturation_step + 5) + 1,
        ):
            saturation = saturation_step / 255.0
            channels = colorsys.hsv_to_rgb(hue / 360.0, saturation, 1.0)
            logical = normalize_rgb(channel * 255.0 for channel in channels)
            mapped = display_rgb_to_wiz_channels(logical)
            distance = _device_distance(mapped, target)
            if distance < best_distance:
                best_distance = distance
                best_rgb = logical
            if best_distance == 0:
                return best_rgb

    return best_rgb


def wiz_channels_to_display_rgb(
    red: int | float,
    green: int | float,
    blue: int | float,
    *,
    cold_white: int | float = 0,
    warm_white: int | float = 0,
) -> RGB:
    """Recover the closest logical sRGB represented by WiZ RGBTW channels."""

    signature = wiz_channels_signature(
        {
            "r": red,
            "g": green,
            "b": blue,
            "c": cold_white,
            "w": warm_white,
        }
    )
    return _decode_signature_cached(signature)


def logical_rgb_from_state(
    state: dict[str, Any],
    *,
    last_logical_rgb: RGB | None = None,
    last_device_signature: tuple[int, int, int, int, int] | None = None,
) -> RGB | None:
    if not all(key in state for key in ("r", "g", "b")):
        return None
    signature = wiz_channels_signature(state)
    if channel_signatures_close(signature, last_device_signature) and last_logical_rgb is not None:
        return normalize_rgb(last_logical_rgb)
    return wiz_channels_to_display_rgb(
        signature[0],
        signature[1],
        signature[2],
        cold_white=signature[3],
        warm_white=signature[4],
    )


__all__ = [
    "RGB",
    "channel_signatures_close",
    "display_rgb_to_wiz_channels",
    "logical_rgb_from_state",
    "normalize_rgb",
    "wiz_channels_signature",
    "wiz_channels_to_display_rgb",
]
