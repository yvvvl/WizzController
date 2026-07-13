from ui.color_utils import (
    harmony_sets,
    hex_to_rgb,
    hsv_to_hex,
    hsv_to_rgb,
    kelvin_to_hex,
    kelvin_to_percent,
    normalize_hex,
    percent_to_kelvin,
    pointer_to_ratio,
    ratio_to_thumb_offset,
    readable_text_color,
    rgb_to_hex,
    rgb_to_hsv,
)


def test_hex_helpers_accept_short_and_full_values():
    assert normalize_hex("#F0A") == "#ff00aa"
    assert normalize_hex("00e5ff") == "#00e5ff"
    assert normalize_hex("bad-value") is None
    assert hex_to_rgb("#00e5ff") == (0, 229, 255)
    assert rgb_to_hex(0, 229, 255) == "#00e5ff"


def test_hsv_rgb_roundtrip_for_neon_color():
    rgb = hsv_to_rgb(306, 100, 100)
    h, s, v = rgb_to_hsv(*rgb)
    assert abs(h - 306) <= 1
    assert s >= 99
    assert v == 100
    assert hsv_to_hex(306, 100, 100) == rgb_to_hex(*rgb)


def test_kelvin_percent_mapping_is_stable():
    assert kelvin_to_percent(2200, 2200, 6500) == 0
    assert kelvin_to_percent(6500, 2200, 6500) == 100
    assert percent_to_kelvin(0, 2200, 6500) == 2200
    assert percent_to_kelvin(100, 2200, 6500) == 6500
    assert kelvin_to_hex(2700).startswith("#")


def test_harmonies_return_clickable_hex_sets():
    groups = harmony_sets(30, 90)
    assert [g["name"] for g in groups] == ["Complementario", "Análogo", "Tríada", "Monocromo"]
    assert all(str(color).startswith("#") for group in groups for color in group["colors"])
    assert readable_text_color("#ffffff") == "#0b1020"


def test_picker_geometry_reaches_edges_without_dragging_outside():
    # Thumb de 24 px dentro de un picker de 300 px: su centro recorre 12..288.
    assert ratio_to_thumb_offset(0, 300, 24) == 0
    assert ratio_to_thumb_offset(1, 300, 24) == 276
    assert pointer_to_ratio(12, 300, 24) == 0
    assert pointer_to_ratio(288, 300, 24) == 1
    assert pointer_to_ratio(150, 300, 24) == 0.5


def test_picker_geometry_clamps_pointer_outside_bounds():
    assert pointer_to_ratio(-50, 300, 24) == 0
    assert pointer_to_ratio(999, 300, 24) == 1
