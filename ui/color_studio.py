from __future__ import annotations

"""Color math, geometry and cached textures for WizZ Color Studio.

WiZ receives direct RGB track values (0..255) and a separate ``dimming`` value.
The picker therefore produces an exact RGB triplet and never hides brightness
inside RGB Value.

The vertical palette axis is *perceptual purity*, not raw HSV saturation.  A
straight white -> pure-hue interpolation in OKLab keeps light reds looking
salmon/red instead of drifting through the synthetic magenta-pink appearance of
``HSV(h, s, 1)``.  The same function generates the PNG and the selected RGB, so
what the user sees under the thumb is exactly what is sent to WiZ.
"""

from dataclasses import dataclass
from functools import lru_cache
import colorsys
import io
import math
from typing import Any, Iterable

from PIL import Image

RGB = tuple[int, int, int]
Point = tuple[float, float]
Lab = tuple[float, float, float]

MIN_KELVIN = 2200
MAX_KELVIN = 6500

# The official WiZ-like palette rises in chroma a little faster than a linear
# white->hue mix.  0.82 keeps a useful pastel band while making the middle of
# the red lane read as light red/salmon rather than bubble-gum pink.
PALETTE_PURITY_EXPONENT = 0.82
DEFAULT_THUMB_DIAMETER = 24.0


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` to an inclusive interval."""

    if low > high:
        low, high = high, low
    return max(low, min(high, float(value)))


def clamp_int(value: int | float, low: int, high: int) -> int:
    return int(round(clamp(float(value), float(low), float(high))))


def normalize_rgb(rgb: Iterable[int | float]) -> RGB:
    values = list(rgb)
    if len(values) < 3:
        raise ValueError("RGB requiere tres componentes")
    return (
        clamp_int(values[0], 0, 255),
        clamp_int(values[1], 0, 255),
        clamp_int(values[2], 0, 255),
    )


# ---------------------------------------------------------------------------
# Standard RGB / HSV helpers (kept for precise input and compatibility)
# ---------------------------------------------------------------------------

def hue_saturation_to_rgb(hue: float, saturation: float) -> RGB:
    """Standard HSV conversion with Value fixed at 100%."""

    hue_norm = (float(hue) % 360.0) / 360.0
    sat_norm = clamp(float(saturation), 0.0, 1.0)
    r, g, b = colorsys.hsv_to_rgb(hue_norm, sat_norm, 1.0)
    return (
        clamp_int(r * 255.0, 0, 255),
        clamp_int(g * 255.0, 0, 255),
        clamp_int(b * 255.0, 0, 255),
    )


def rgb_to_hsv(rgb: Iterable[int | float]) -> tuple[float, float, float]:
    """Return ``(hue_degrees, saturation, value)`` for an RGB triplet."""

    r, g, b = normalize_rgb(rgb)
    hue, saturation, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return ((hue * 360.0) % 360.0, saturation, value)


def rgb_to_hue_saturation(rgb: Iterable[int | float]) -> tuple[float, float]:
    hue, saturation, _ = rgb_to_hsv(rgb)
    return hue, saturation


def rgb_to_hex(rgb: Iterable[int | float], *, upper: bool = False) -> str:
    r, g, b = normalize_rgb(rgb)
    value = f"#{r:02x}{g:02x}{b:02x}"
    return value.upper() if upper else value


def parse_hex_color(value: str) -> RGB:
    raw = str(value or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        raise ValueError("HEX debe tener 3 o 6 dígitos")
    try:
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError as exc:
        raise ValueError("HEX inválido") from exc


def contrast_text_color(rgb: Iterable[int | float]) -> str:
    """Choose readable black/white foreground using relative luminance."""

    r, g, b = normalize_rgb(rgb)

    def linear(channel: int) -> float:
        value = channel / 255.0
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
    return "#0b1020" if luminance >= 0.48 else "#ffffff"


# ---------------------------------------------------------------------------
# OKLab perceptual palette
# ---------------------------------------------------------------------------

def _srgb_to_linear(channel: float) -> float:
    value = clamp(channel, 0.0, 1.0)
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(channel: float) -> float:
    if channel <= 0.0031308:
        value = 12.92 * channel
    else:
        value = 1.055 * (channel ** (1.0 / 2.4)) - 0.055
    return clamp(value, 0.0, 1.0)


def _cbrt(value: float) -> float:
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def rgb_to_oklab(rgb: Iterable[int | float]) -> Lab:
    """Convert sRGB 0..255 to OKLab."""

    r8, g8, b8 = normalize_rgb(rgb)
    r = _srgb_to_linear(r8 / 255.0)
    g = _srgb_to_linear(g8 / 255.0)
    b = _srgb_to_linear(b8 / 255.0)

    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_ = _cbrt(l)
    m_ = _cbrt(m)
    s_ = _cbrt(s)

    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_rgb(lab: Iterable[float]) -> RGB:
    """Convert OKLab to clipped sRGB 0..255."""

    values = list(lab)
    if len(values) < 3:
        raise ValueError("OKLab requiere tres componentes")
    L, a, b = float(values[0]), float(values[1]), float(values[2])

    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_ * l_ * l_
    m = m_ * m_ * m_
    s = s_ * s_ * s_

    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    blue = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return (
        clamp_int(_linear_to_srgb(r) * 255.0, 0, 255),
        clamp_int(_linear_to_srgb(g) * 255.0, 0, 255),
        clamp_int(_linear_to_srgb(blue) * 255.0, 0, 255),
    )


_WHITE_OKLAB = rgb_to_oklab((255, 255, 255))


def _purity_to_mix(purity: float) -> float:
    return clamp(purity, 0.0, 1.0) ** PALETTE_PURITY_EXPONENT


def _mix_to_purity(mix: float) -> float:
    return clamp(mix, 0.0, 1.0) ** (1.0 / PALETTE_PURITY_EXPONENT)


def hue_purity_to_rgb(hue: float, purity: float) -> RGB:
    """Return the exact RGB shown by the smart-light palette.

    ``purity=0`` is white and ``purity=1`` is the fully saturated hue.  The
    interpolation happens in OKLab, then the result is clipped into the sRGB
    gamut accepted by WiZ's direct RGB tracks.
    """

    pure_rgb = hue_saturation_to_rgb(hue, 1.0)
    pure_lab = rgb_to_oklab(pure_rgb)
    mix = _purity_to_mix(purity)
    lab = tuple(
        white + (pure - white) * mix
        for white, pure in zip(_WHITE_OKLAB, pure_lab)
    )
    return oklab_to_rgb(lab)


@lru_cache(maxsize=4096)
def _pure_hue_oklab(tenths: int) -> Lab:
    hue = (int(tenths) % 3600) / 10.0
    return rgb_to_oklab(hue_saturation_to_rgb(hue, 1.0))


def _project_palette_lane(value_lab: Lab, hue: float) -> tuple[float, float]:
    pure_lab = _pure_hue_oklab(round((hue % 360.0) * 10.0))
    direction = tuple(pure - white for white, pure in zip(_WHITE_OKLAB, pure_lab))
    relative = tuple(value - white for white, value in zip(_WHITE_OKLAB, value_lab))
    denominator = sum(component * component for component in direction)
    if denominator <= 1e-12:
        return 0.0, float("inf")
    mix = clamp(sum(a * b for a, b in zip(relative, direction)) / denominator, 0.0, 1.0)
    predicted = tuple(
        white + component * mix
        for white, component in zip(_WHITE_OKLAB, direction)
    )
    error = sum((actual - estimate) ** 2 for actual, estimate in zip(value_lab, predicted))
    return mix, error


def rgb_to_hue_purity(rgb: Iterable[int | float]) -> tuple[float, float]:
    """Find the nearest perceptual palette lane for an arbitrary RGB.

    The OKLab white->hue path can shift the resulting HSV hue by several
    degrees (that shift is what makes light red look salmon rather than pink),
    so a plain ``rgb_to_hsv`` inverse is not sufficient.  A cached coarse search
    plus a local tenth-degree refinement restores palette-generated colours
    accurately and remains cheap for occasional external-state synchronisation.
    """

    normalized = normalize_rgb(rgb)
    if max(normalized) - min(normalized) <= 1:
        return 0.0, 0.0

    value_lab = rgb_to_oklab(normalized)
    hsv_hue, _, _ = rgb_to_hsv(normalized)
    candidates = {float(hue) for hue in range(0, 360, 5)}
    candidates.update((hsv_hue + offset) % 360.0 for offset in range(-24, 25))

    best_hue = 0.0
    best_mix = 0.0
    best_error = float("inf")
    for hue in candidates:
        mix, error = _project_palette_lane(value_lab, hue)
        if error < best_error:
            best_hue, best_mix, best_error = hue, mix, error

    center_tenths = round(best_hue * 10.0)
    for tenths in range(center_tenths - 15, center_tenths + 16):
        hue = (tenths % 3600) / 10.0
        mix, error = _project_palette_lane(value_lab, hue)
        if error < best_error:
            best_hue, best_mix, best_error = hue, mix, error

    return best_hue % 360.0, _mix_to_purity(best_mix)


def palette_rgb_at_ratios(x_ratio: float, y_ratio: float) -> RGB:
    """Sample the palette model at normalized coordinates."""

    hue = clamp(x_ratio, 0.0, 1.0) * 360.0
    return hue_purity_to_rgb(hue, clamp(y_ratio, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Geometry: visual track is full-size; thumbs remain fully contained
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PaletteGeometry:
    """2-D palette geometry with the full thumb kept inside the image.

    The texture includes replicated edge padding equal to the thumb radius.
    Pointer ratios and texture pixels use the same usable rectangle, so all
    endpoints remain reachable without drawing half the thumb outside.
    """

    image_width: float
    image_height: float
    thumb_diameter: float = DEFAULT_THUMB_DIAMETER

    def __post_init__(self) -> None:
        if self.image_width <= self.thumb_diameter or self.image_height <= self.thumb_diameter:
            raise ValueError("La paleta debe ser mayor que el thumb")
        if self.thumb_diameter <= 0:
            raise ValueError("El thumb necesita un diámetro positivo")

    @property
    def radius(self) -> float:
        return self.thumb_diameter / 2.0

    @property
    def usable_width(self) -> float:
        return self.image_width - self.thumb_diameter

    @property
    def usable_height(self) -> float:
        return self.image_height - self.thumb_diameter

    @property
    def outer_width(self) -> float:
        return self.image_width

    @property
    def outer_height(self) -> float:
        return self.image_height

    @property
    def image_left(self) -> float:
        return 0.0

    @property
    def image_top(self) -> float:
        return 0.0

    def clamp_pointer(self, x: float, y: float) -> Point:
        return (
            clamp(x, self.radius, self.image_width - self.radius),
            clamp(y, self.radius, self.image_height - self.radius),
        )

    def pointer_to_ratios(self, x: float, y: float) -> Point:
        cx, cy = self.clamp_pointer(x, y)
        return (
            (cx - self.radius) / self.usable_width,
            (cy - self.radius) / self.usable_height,
        )

    def pixel_to_ratios(self, x: float, y: float) -> Point:
        """Map an image pixel through the same edge padding used by the thumb."""

        return self.pointer_to_ratios(x, y)

    def pointer_to_hue_purity(self, x: float, y: float) -> tuple[float, float]:
        x_ratio, y_ratio = self.pointer_to_ratios(x, y)
        return x_ratio * 360.0, y_ratio

    def hue_purity_to_ratios(self, hue: float, purity: float) -> Point:
        raw_hue = float(hue)
        if math.isclose(raw_hue, 360.0, abs_tol=1e-9):
            x_ratio = 1.0
        else:
            x_ratio = (raw_hue % 360.0) / 360.0
        return x_ratio, clamp(purity, 0.0, 1.0)

    def hue_purity_to_pointer(self, hue: float, purity: float) -> Point:
        x_ratio, y_ratio = self.hue_purity_to_ratios(hue, purity)
        return (
            self.radius + x_ratio * self.usable_width,
            self.radius + y_ratio * self.usable_height,
        )

    def hue_purity_to_thumb_left_top(self, hue: float, purity: float) -> Point:
        center_x, center_y = self.hue_purity_to_pointer(hue, purity)
        return center_x - self.radius, center_y - self.radius

    # Compatibility names retained for one release cycle.
    def pointer_to_hue_saturation(self, x: float, y: float) -> tuple[float, float]:
        return self.pointer_to_hue_purity(x, y)

    def hue_saturation_to_ratios(self, hue: float, saturation: float) -> Point:
        return self.hue_purity_to_ratios(hue, saturation)

    def hue_saturation_to_pointer(self, hue: float, saturation: float) -> Point:
        return self.hue_purity_to_pointer(hue, saturation)

    def hue_saturation_to_thumb_left_top(self, hue: float, saturation: float) -> Point:
        return self.hue_purity_to_thumb_left_top(hue, saturation)


@dataclass(frozen=True, slots=True)
class TrackGeometry:
    """One-dimensional track whose thumb remains completely inside the bar."""

    length: float
    thumb_diameter: float = DEFAULT_THUMB_DIAMETER
    thickness: float = 34.0

    def __post_init__(self) -> None:
        if self.length <= self.thumb_diameter or self.thumb_diameter <= 0 or self.thickness <= 0:
            raise ValueError("Geometría de track inválida")

    @property
    def radius(self) -> float:
        return self.thumb_diameter / 2.0

    @property
    def usable_length(self) -> float:
        return self.length - self.thumb_diameter

    @property
    def outer_width(self) -> float:
        return self.length

    @property
    def outer_height(self) -> float:
        return max(self.thickness, self.thumb_diameter)

    @property
    def track_left(self) -> float:
        return 0.0

    @property
    def track_top(self) -> float:
        return (self.outer_height - self.thickness) / 2.0

    @property
    def thumb_top(self) -> float:
        return (self.outer_height - self.thumb_diameter) / 2.0

    def pointer_to_ratio(self, x: float) -> float:
        center = clamp(x, self.radius, self.length - self.radius)
        return (center - self.radius) / self.usable_length

    def pixel_to_ratio(self, x: float) -> float:
        return self.pointer_to_ratio(x)

    def ratio_to_pointer(self, ratio: float) -> float:
        return self.radius + clamp(ratio, 0.0, 1.0) * self.usable_length

    def ratio_to_thumb_left(self, ratio: float) -> float:
        return self.ratio_to_pointer(ratio) - self.radius


@dataclass(slots=True)
class DragSnapshot:
    local_anchor: Point | None = None
    global_anchor: Point | None = None
    last_point: Point | None = None
    active: bool = False


class GlobalDragTracker:
    """Stable local coordinates even when Flet reports wrapped edge positions."""

    def __init__(self, width: float, height: float) -> None:
        self.width = float(width)
        self.height = float(height)
        self.state = DragSnapshot()

    def resize(self, width: float, height: float) -> None:
        self.width = max(1.0, float(width))
        self.height = max(1.0, float(height))
        if self.state.last_point is not None:
            self.state.last_point = self._clamp(*self.state.last_point)

    def tap(self, event: Any) -> Point | None:
        local = _event_point(event, "local_position", "local_x", "local_y")
        if local is None:
            return None
        point = self._clamp(*local)
        self.state.last_point = point
        return point

    def begin(self, event: Any) -> Point | None:
        local = _event_point(event, "local_position", "local_x", "local_y")
        global_point = _event_point(event, "global_position", "global_x", "global_y")
        if local is None and global_point is None:
            return None
        if local is None:
            local = self.state.last_point or (0.0, 0.0)
        point = self._clamp(*local)
        self.state = DragSnapshot(
            local_anchor=point,
            global_anchor=global_point,
            last_point=point,
            active=True,
        )
        return point

    def move(self, event: Any) -> Point | None:
        if not self.state.active:
            return self.begin(event)

        candidate: Point | None = None
        global_point = _event_point(event, "global_position", "global_x", "global_y")
        if (
            global_point is not None
            and self.state.global_anchor is not None
            and self.state.local_anchor is not None
        ):
            candidate = (
                self.state.local_anchor[0] + global_point[0] - self.state.global_anchor[0],
                self.state.local_anchor[1] + global_point[1] - self.state.global_anchor[1],
            )

        if candidate is None:
            delta = _event_point(event, "global_delta", "delta_x", "delta_y")
            if delta is None:
                delta = _event_point(event, "local_delta", "delta_x", "delta_y")
            if delta is not None and self.state.last_point is not None:
                candidate = (
                    self.state.last_point[0] + delta[0],
                    self.state.last_point[1] + delta[1],
                )

        if candidate is None:
            candidate = _event_point(event, "local_position", "local_x", "local_y")

        if candidate is None:
            return self.state.last_point

        point = self._clamp(*candidate)
        self.state.last_point = point
        return point

    def end(self, event: Any | None = None) -> Point | None:
        point = self.move(event) if event is not None else self.state.last_point
        self.state.active = False
        return point

    def cancel(self) -> Point | None:
        point = self.state.last_point
        self.state.active = False
        return point

    def _clamp(self, x: float, y: float) -> Point:
        return clamp(x, 0.0, self.width), clamp(y, 0.0, self.height)


def _coerce_point(value: Any) -> Point | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    x = getattr(value, "x", None)
    y = getattr(value, "y", None)
    if x is None or y is None:
        return None
    try:
        return float(x), float(y)
    except (TypeError, ValueError):
        return None


def _event_point(event: Any, object_name: str, x_name: str, y_name: str) -> Point | None:
    if event is None:
        return None
    point = _coerce_point(getattr(event, object_name, None))
    if point is not None:
        return point
    x = getattr(event, x_name, None)
    y = getattr(event, y_name, None)
    if x is None or y is None:
        return None
    try:
        return float(x), float(y)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# CCT helpers
# ---------------------------------------------------------------------------

def ratio_to_kelvin(ratio: float, minimum: int = MIN_KELVIN, maximum: int = MAX_KELVIN) -> int:
    minimum, maximum = sorted((int(minimum), int(maximum)))
    return clamp_int(minimum + clamp(ratio, 0.0, 1.0) * (maximum - minimum), minimum, maximum)


def kelvin_to_ratio(kelvin: int | float, minimum: int = MIN_KELVIN, maximum: int = MAX_KELVIN) -> float:
    minimum, maximum = sorted((int(minimum), int(maximum)))
    if minimum == maximum:
        return 0.0
    return (clamp(float(kelvin), minimum, maximum) - minimum) / (maximum - minimum)


def kelvin_to_rgb(kelvin: int | float) -> RGB:
    """Return a UI-only CCT preview colour; WiZ still receives Kelvin."""

    anchors: tuple[tuple[int, RGB], ...] = (
        (2200, (255, 154, 60)),
        (2700, (255, 193, 135)),
        (3500, (255, 224, 190)),
        (4000, (255, 241, 223)),
        (5000, (247, 252, 255)),
        (6500, (214, 236, 255)),
    )
    value = clamp(float(kelvin), anchors[0][0], anchors[-1][0])
    for index in range(len(anchors) - 1):
        left_k, left_rgb = anchors[index]
        right_k, right_rgb = anchors[index + 1]
        if value <= right_k:
            ratio = (value - left_k) / max(1.0, right_k - left_k)
            return normalize_rgb(
                left_rgb[channel] + (right_rgb[channel] - left_rgb[channel]) * ratio
                for channel in range(3)
            )
    return anchors[-1][1]


def white_label(kelvin: int) -> str:
    value = int(kelvin)
    if value <= 2350:
        return "Vela"
    if value <= 3100:
        return "Cálido"
    if value <= 4300:
        return "Neutro"
    if value <= 5600:
        return "Día"
    return "Frío"


# ---------------------------------------------------------------------------
# Cached textures. Edge padding mirrors thumb geometry exactly.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=24)
def palette_png(
    width: int,
    height: int,
    thumb_diameter: float = DEFAULT_THUMB_DIAMETER,
) -> bytes:
    """Generate the perceptual hue/purity texture and cache it by size."""

    width = max(int(math.ceil(thumb_diameter)) + 2, int(width))
    height = max(int(math.ceil(thumb_diameter)) + 2, int(height))
    geometry = PaletteGeometry(width, height, float(thumb_diameter))
    pixels: list[RGB] = []
    for y in range(height):
        for x in range(width):
            x_ratio, y_ratio = geometry.pixel_to_ratios(x, y)
            pixels.append(palette_rgb_at_ratios(x_ratio, y_ratio))
    image = Image.new("RGB", (width, height))
    image.putdata(pixels)
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()


@lru_cache(maxsize=24)
def kelvin_gradient_png(
    width: int,
    height: int,
    minimum: int,
    maximum: int,
    thumb_diameter: float = DEFAULT_THUMB_DIAMETER,
) -> bytes:
    width = max(int(math.ceil(thumb_diameter)) + 2, int(width))
    height = max(2, int(height))
    geometry = TrackGeometry(width, float(thumb_diameter), height)
    row = [
        kelvin_to_rgb(
            ratio_to_kelvin(geometry.pixel_to_ratio(x), minimum, maximum)
        )
        for x in range(width)
    ]
    image = Image.new("RGB", (width, height))
    image.putdata(row * height)
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()


__all__ = [
    "DEFAULT_THUMB_DIAMETER",
    "GlobalDragTracker",
    "MAX_KELVIN",
    "MIN_KELVIN",
    "PALETTE_PURITY_EXPONENT",
    "PaletteGeometry",
    "Point",
    "RGB",
    "TrackGeometry",
    "clamp",
    "clamp_int",
    "contrast_text_color",
    "hue_purity_to_rgb",
    "hue_saturation_to_rgb",
    "kelvin_gradient_png",
    "kelvin_to_ratio",
    "kelvin_to_rgb",
    "normalize_rgb",
    "oklab_to_rgb",
    "palette_png",
    "palette_rgb_at_ratios",
    "parse_hex_color",
    "ratio_to_kelvin",
    "rgb_to_hex",
    "rgb_to_hsv",
    "rgb_to_hue_purity",
    "rgb_to_hue_saturation",
    "rgb_to_oklab",
    "white_label",
]
