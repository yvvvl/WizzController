from __future__ import annotations

import colorsys
import re

_HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")


def clamp(value: float | int, lo: float | int, hi: float | int) -> float:
    return max(float(lo), min(float(hi), float(value)))


# ---------------------------------------------------------------------------
# Picker geometry helpers
# ---------------------------------------------------------------------------
def pointer_to_ratio(position: int | float, length: int | float, thumb_size: int | float) -> float:
    """Mapea el cursor al recorrido real del centro del thumb (0..1).

    El centro del thumb no viaja desde 0 hasta ``length``: se mueve desde
    ``thumb_size / 2`` hasta ``length - thumb_size / 2``. Usar el ancho
    completo provoca que el usuario deba arrastrar fuera del picker para
    alcanzar 0% o 100%.
    """
    total = max(1.0, float(length))
    thumb = max(0.0, min(float(thumb_size), total))
    radius = thumb / 2.0
    travel = max(1.0, total - thumb)
    return clamp((float(position) - radius) / travel, 0.0, 1.0)


def ratio_to_thumb_offset(ratio: int | float, length: int | float, thumb_size: int | float) -> float:
    """Devuelve la posición left/top del thumb para un ratio 0..1."""
    total = max(1.0, float(length))
    thumb = max(0.0, min(float(thumb_size), total))
    travel = max(0.0, total - thumb)
    return clamp(ratio, 0.0, 1.0) * travel


def normalize_hex(value: object, *, fallback: str | None = None) -> str | None:
    """Devuelve un HEX normalizado '#rrggbb' o fallback/None si es inválido."""
    text = str(value or "").strip().lstrip("#")
    if len(text) == 3 and all(ch in "0123456789abcdefABCDEF" for ch in text):
        text = "".join(ch * 2 for ch in text)
    if len(text) == 6 and _HEX_RE.match(text):
        return f"#{text.lower()}"
    return fallback


def hex_to_rgb(value: object) -> tuple[int, int, int] | None:
    h = normalize_hex(value)
    if h is None:
        return None
    raw = h[1:]
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def rgb_to_hex(r: int | float, g: int | float, b: int | float) -> str:
    rr = int(round(clamp(r, 0, 255)))
    gg = int(round(clamp(g, 0, 255)))
    bb = int(round(clamp(b, 0, 255)))
    return f"#{rr:02x}{gg:02x}{bb:02x}"


def hsv_to_rgb(hue: int | float, sat: int | float, val: int | float = 100) -> tuple[int, int, int]:
    h = (float(hue) % 360.0) / 360.0
    s = clamp(sat, 0, 100) / 100.0
    v = clamp(val, 0, 100) / 100.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return round(r * 255), round(g * 255), round(b * 255)


def rgb_to_hsv(r: int | float, g: int | float, b: int | float) -> tuple[float, float, float]:
    rr = clamp(r, 0, 255) / 255.0
    gg = clamp(g, 0, 255) / 255.0
    bb = clamp(b, 0, 255) / 255.0
    h, s, v = colorsys.rgb_to_hsv(rr, gg, bb)
    return min(359.999, h * 360.0), s * 100.0, v * 100.0


def kelvin_to_percent(kelvin: int | float, lo: int | float, hi: int | float) -> int:
    low = int(lo)
    high = int(hi)
    if high <= low:
        return 50
    k = clamp(kelvin, low, high)
    return round((k - low) * 100.0 / (high - low))


def percent_to_kelvin(percent: int | float, lo: int | float, hi: int | float) -> int:
    low = int(lo)
    high = int(hi)
    if high <= low:
        return low
    pct = clamp(percent, 0, 100) / 100.0
    return round(low + (high - low) * pct)


def interpolate_hex(stops: list[tuple[float, str]], position: float) -> str:
    """Interpola colores HEX. position espera 0..1."""
    if not stops:
        return "#ffffff"
    pos = clamp(position, 0, 1)
    ordered = sorted((clamp(p, 0, 1), normalize_hex(c, fallback="#ffffff") or "#ffffff") for p, c in stops)
    if pos <= ordered[0][0]:
        return ordered[0][1]
    if pos >= ordered[-1][0]:
        return ordered[-1][1]
    for idx in range(1, len(ordered)):
        left_p, left_c = ordered[idx - 1]
        right_p, right_c = ordered[idx]
        if left_p <= pos <= right_p:
            span = max(0.000001, right_p - left_p)
            t = (pos - left_p) / span
            lr, lg, lb = hex_to_rgb(left_c) or (255, 255, 255)
            rr, rg, rb = hex_to_rgb(right_c) or (255, 255, 255)
            return rgb_to_hex(lr + (rr - lr) * t, lg + (rg - lg) * t, lb + (rb - lb) * t)
    return ordered[-1][1]

# ---------------------------------------------------------------------------
# Color Studio helpers
# ---------------------------------------------------------------------------
def hsv_to_hex(hue: int | float, sat: int | float = 100, val: int | float = 100) -> str:
    return rgb_to_hex(*hsv_to_rgb(hue, sat, val))


def kelvin_to_rgb(kelvin: int | float) -> tuple[int, int, int]:
    """Aproximación visual de temperatura de color para preview UI.

    WiZ recibe Kelvin reales; este RGB solo se usa para pintar controles.
    """
    import math

    k = clamp(kelvin, 1000, 12000) / 100.0
    if k <= 66.0:
        r = 255.0
        g = 99.4708025861 * math.log(max(k, 1.0)) - 161.1195681661
        b = 0.0 if k <= 19.0 else 138.5177312231 * math.log(max(k - 10.0, 1.0)) - 305.0447927307
    else:
        r = 329.698727446 * ((k - 60.0) ** -0.1332047592)
        g = 288.1221695283 * ((k - 60.0) ** -0.0755148492)
        b = 255.0
    return int(round(clamp(r, 0, 255))), int(round(clamp(g, 0, 255))), int(round(clamp(b, 0, 255)))


def kelvin_to_hex(kelvin: int | float) -> str:
    return rgb_to_hex(*kelvin_to_rgb(kelvin))


def readable_text_color(hex_color: object) -> str:
    rgb = hex_to_rgb(hex_color) or (255, 255, 255)
    r, g, b = rgb
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    return "#0b1020" if luminance > 0.62 else "white"


def harmony_sets(hue: int | float, sat: int | float = 100) -> list[dict[str, object]]:
    h = float(hue) % 360.0
    s = max(35.0, min(100.0, float(sat)))
    return [
        {"name": "Complementario", "note": "contraste fuerte", "colors": [hsv_to_hex(h, s, 100), hsv_to_hex(h + 180, s, 100)]},
        {"name": "Análogo", "note": "suave y coherente", "colors": [hsv_to_hex(h - 28, s, 100), hsv_to_hex(h, s, 100), hsv_to_hex(h + 28, s, 100)]},
        {"name": "Tríada", "note": "gamer / vibrante", "colors": [hsv_to_hex(h, s, 100), hsv_to_hex(h + 120, s, 100), hsv_to_hex(h + 240, s, 100)]},
        {"name": "Monocromo", "note": "mismo color, intensidad", "colors": [hsv_to_hex(h, max(20, s - 45), 100), hsv_to_hex(h, max(30, s - 20), 100), hsv_to_hex(h, s, 100)]},
    ]


def unique_hexes(values, limit: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        h = normalize_hex(value)
        if not h or h in seen:
            continue
        out.append(h)
        seen.add(h)
        if len(out) >= limit:
            break
    return out
