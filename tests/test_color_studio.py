from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from PIL import Image
import pytest

from ui.color_studio import (
    GlobalDragTracker,
    PALETTE_PURITY_EXPONENT,
    PaletteGeometry,
    TrackGeometry,
    hue_purity_to_rgb,
    hue_saturation_to_rgb,
    kelvin_gradient_png,
    kelvin_to_ratio,
    palette_png,
    parse_hex_color,
    ratio_to_kelvin,
    rgb_to_hex,
    rgb_to_hsv,
    rgb_to_hue_purity,
)


@pytest.mark.parametrize(
    ("hue", "expected"),
    [
        (0, (255, 0, 0)),
        (60, (255, 255, 0)),
        (120, (0, 255, 0)),
        (180, (0, 255, 255)),
        (240, (0, 0, 255)),
        (300, (255, 0, 255)),
        (360, (255, 0, 0)),
    ],
)
def test_primary_hues_are_exact(hue: float, expected: tuple[int, int, int]) -> None:
    assert hue_purity_to_rgb(hue, 1.0) == expected
    assert hue_saturation_to_rgb(hue, 1.0) == expected


def test_perceptual_red_lane_looks_light_red_not_magenta_pink() -> None:
    # Standard HSV at S=.5 is #FF8080. The OKLab palette intentionally shifts
    # the midpoint toward a warmer, clearer light red like the WiZ mobile UI.
    assert PALETTE_PURITY_EXPONENT == pytest.approx(0.82)
    assert hue_purity_to_rgb(0, 0.5) == (255, 148, 131)
    assert hue_purity_to_rgb(0, 0.5) != hue_saturation_to_rgb(0, 0.5)


def test_zero_purity_is_white_for_every_hue() -> None:
    for hue in (0, 45, 180, 359.9, 360):
        assert hue_purity_to_rgb(hue, 0.0) == (255, 255, 255)


def test_hex_parsing_and_formatting() -> None:
    assert parse_hex_color("#f00") == (255, 0, 0)
    assert parse_hex_color("12AbEf") == (18, 171, 239)
    assert rgb_to_hex((18, 171, 239), upper=True) == "#12ABEF"
    with pytest.raises(ValueError):
        parse_hex_color("pink")


def test_palette_geometry_contains_thumb_and_reaches_all_values() -> None:
    geometry = PaletteGeometry(320, 100, 24)
    assert geometry.outer_width == 320
    assert geometry.outer_height == 100
    assert geometry.usable_width == 296
    assert geometry.usable_height == 76

    assert geometry.hue_purity_to_thumb_left_top(0, 0) == (0, 0)
    assert geometry.hue_purity_to_thumb_left_top(360, 0) == (296, 0)
    assert geometry.hue_purity_to_thumb_left_top(0, 1) == (0, 76)
    assert geometry.hue_purity_to_thumb_left_top(360, 1) == (296, 76)

    # Pointer coordinates are thumb centers, so the center never leaves the
    # radius-inset usable rectangle.
    assert geometry.pointer_to_hue_purity(-999, -999) == (0, 0)
    assert geometry.pointer_to_hue_purity(999, 999) == (360, 1)


def test_palette_round_trip_geometry() -> None:
    geometry = PaletteGeometry(480, 144, 24)
    for hue, purity in ((0, 0), (60, 0.25), (180, 0.5), (300, 0.75), (360, 1)):
        x, y = geometry.hue_purity_to_pointer(hue, purity)
        restored_hue, restored_purity = geometry.pointer_to_hue_purity(x, y)
        assert restored_hue == pytest.approx(hue)
        assert restored_purity == pytest.approx(purity)


def test_generated_texture_matches_picker_math_under_thumb_centers() -> None:
    width, height, thumb = 140, 52, 24
    geometry = PaletteGeometry(width, height, thumb)
    image = Image.open(BytesIO(palette_png(width, height, thumb))).convert("RGB")

    for hue, purity in ((0, 0), (0, 0.5), (60, 1), (180, 0.4), (300, 0.8), (360, 1)):
        x, y = geometry.hue_purity_to_pointer(hue, purity)
        pixel = image.getpixel((round(x), round(y)))
        expected_hue, expected_purity = geometry.pixel_to_ratios(round(x), round(y))
        expected = hue_purity_to_rgb(expected_hue * 360.0, expected_purity)
        assert pixel == expected


def test_texture_edges_are_padded_for_a_contained_thumb() -> None:
    width, height, thumb = 140, 52, 24
    image = Image.open(BytesIO(palette_png(width, height, thumb))).convert("RGB")
    # Edge padding repeats endpoint values, so the thumb can remain inside while
    # still selecting white/pure red exactly.
    assert image.getpixel((0, 0)) == (255, 255, 255)
    assert image.getpixel((12, 0)) == (255, 255, 255)
    assert image.getpixel((0, height - 1)) == (255, 0, 0)
    assert image.getpixel((width - 1, height - 1)) == (255, 0, 0)


def test_texture_is_cached_by_size_and_thumb() -> None:
    assert palette_png(120, 40, 24) is palette_png(120, 40, 24)
    assert palette_png(121, 40, 24) != palette_png(120, 40, 24)
    assert palette_png(120, 40, 20) != palette_png(120, 40, 24)


def test_rgb_hue_purity_roundtrip_for_palette_colors() -> None:
    for hue, purity in ((0, 0.25), (30, 0.5), (120, 0.75), (240, 1.0), (300, 0.4)):
        rgb = hue_purity_to_rgb(hue, purity)
        restored_hue, restored_purity = rgb_to_hue_purity(rgb)
        # Quantized sRGB can shift a few degrees at very low chroma.
        hue_delta = min(abs(restored_hue - hue), 360 - abs(restored_hue - hue))
        assert hue_delta <= 15.0
        assert restored_purity == pytest.approx(purity, abs=0.035)


def test_rgb_hsv_roundtrip_preserves_precise_value() -> None:
    hue, saturation, value = rgb_to_hsv((128, 0, 0))
    assert hue == pytest.approx(0)
    assert saturation == pytest.approx(1)
    assert value == pytest.approx(128 / 255)


def test_kelvin_track_endpoints_and_clamp() -> None:
    assert ratio_to_kelvin(0, 2200, 6500) == 2200
    assert ratio_to_kelvin(1, 2200, 6500) == 6500
    assert ratio_to_kelvin(-10, 2200, 6500) == 2200
    assert ratio_to_kelvin(10, 2200, 6500) == 6500
    assert kelvin_to_ratio(2200, 2200, 6500) == 0
    assert kelvin_to_ratio(6500, 2200, 6500) == 1


def test_track_geometry_keeps_thumb_fully_inside_bar() -> None:
    geometry = TrackGeometry(400, 24, 34)
    assert geometry.outer_width == 400
    assert geometry.outer_height == 34
    assert geometry.ratio_to_thumb_left(0) == 0
    assert geometry.ratio_to_thumb_left(1) == 376
    assert geometry.ratio_to_thumb_left(1) + geometry.thumb_diameter == geometry.outer_width
    assert geometry.pointer_to_ratio(-100) == 0
    assert geometry.pointer_to_ratio(1000) == 1


def test_kelvin_gradient_padding_matches_track_geometry() -> None:
    width, height, thumb = 80, 12, 24
    geometry = TrackGeometry(width, thumb, height)
    image = Image.open(BytesIO(kelvin_gradient_png(width, height, 2200, 6500, thumb))).convert("RGB")
    assert image.size == (80, 12)
    # Pixels under endpoint thumb centers and outer padding match exactly.
    left_center = round(geometry.ratio_to_pointer(0))
    right_center = round(geometry.ratio_to_pointer(1))
    assert image.getpixel((0, 0)) == image.getpixel((left_center, 0))
    assert image.getpixel((width - 1, 0)) == image.getpixel((right_center, 0))
    assert image.getpixel((left_center, 0)) != image.getpixel((right_center, 0))


def _event(local=None, global_point=None, global_delta=None):
    return SimpleNamespace(
        local_position=SimpleNamespace(x=local[0], y=local[1]) if local else None,
        global_position=SimpleNamespace(x=global_point[0], y=global_point[1]) if global_point else None,
        global_delta=SimpleNamespace(x=global_delta[0], y=global_delta[1]) if global_delta else None,
    )


def test_global_drag_tracker_clamps_outside_and_reenters_smoothly() -> None:
    tracker = GlobalDragTracker(320, 100)
    assert tracker.begin(_event((100, 50), (500, 300))) == (100, 50)
    assert tracker.move(_event((0, 0), (900, 300))) == (320, 50)
    assert tracker.move(_event((0, 0), (650, 300))) == (250, 50)
    assert tracker.end() == (250, 50)


def test_global_drag_tracker_uses_delta_fallback() -> None:
    tracker = GlobalDragTracker(100, 60)
    tracker.begin(_event((20, 20)))
    assert tracker.move(_event(global_delta=(200, -100))) == (100, 0)
    assert tracker.cancel() == (100, 0)
