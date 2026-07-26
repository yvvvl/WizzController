from dataclasses import FrozenInstanceError

import pytest

from core.effects.models import (
    DeviceCapabilities,
    EffectFrame,
    RGBColor,
    RGBICFrame,
    RGBICZone,
)


def test_effect_frame_is_immutable_and_normalizes_collections():
    red = RGBColor(255, 0, 0)
    green = RGBColor(0, 255, 0)

    frame = EffectFrame(
        timestamp=1.25,
        target="living-room",
        colors=[red, green],
        zones=[1, 2],
    )

    assert frame.colors == (red, green)
    assert frame.zones == (1, 2)
    with pytest.raises(FrozenInstanceError):
        frame.target = "bedroom"


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ((-1, 0, 0), "between 0 and 255"),
        ((0, 256, 0), "between 0 and 255"),
        ((0, 0, 1.5), "integers"),
    ],
)
def test_rgb_color_rejects_invalid_channels(values, message):
    with pytest.raises(ValueError, match=message):
        RGBColor(*values)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timestamp": -0.1, "target": "lamp", "colors": []},
        {"timestamp": float("inf"), "target": "lamp", "colors": []},
        {"timestamp": 0, "target": " ", "colors": []},
        {
            "timestamp": 0,
            "target": "lamp",
            "colors": [RGBColor(1, 2, 3)],
            "zones": [1, 2],
        },
        {
            "timestamp": 0,
            "target": "lamp",
            "colors": [RGBColor(1, 2, 3)],
            "zones": [13],
        },
    ],
)
def test_effect_frame_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        EffectFrame(**kwargs)


def test_rgbic_frame_accepts_twelve_zones_and_preserves_weights():
    zones = [
        RGBICZone(
            color=RGBColor(index, index + 1, index + 2),
            weight=index + 1,
        )
        for index in range(12)
    ]

    frame = RGBICFrame(zones=zones)

    assert len(frame.zones) == 12
    assert frame.zones[0].weight == 1
    assert frame.zones[-1].weight == 12


def test_rgbic_zone_accepts_fractional_relative_weight():
    zone = RGBICZone(RGBColor(1, 2, 3), weight=1.5)

    assert zone.weight == 1.5


def test_rgbic_frame_accepts_empty_zones():
    assert RGBICFrame(zones=[]).zones == ()


def test_rgbic_frame_rejects_more_than_twelve_zones():
    zone = RGBICZone(RGBColor(1, 2, 3))

    with pytest.raises(ValueError, match="at most 12"):
        RGBICFrame(zones=[zone] * 13)


@pytest.mark.parametrize("weight", [0, -1, float("inf"), float("nan"), True, "2"])
def test_rgbic_zone_rejects_invalid_weight(weight):
    with pytest.raises(ValueError, match="positive finite number"):
        RGBICZone(RGBColor(1, 2, 3), weight=weight)


def test_device_capabilities_can_describe_twelve_rgbic_zones():
    capabilities = DeviceCapabilities(
        rgb=True,
        white=True,
        scenes=True,
        rgbic_zones=12,
    )

    assert capabilities.rgb
    assert capabilities.white
    assert capabilities.scenes
    assert capabilities.rgbic_zones == 12


@pytest.mark.parametrize("zone_count", [0, -1, 13, 1.5, True])
def test_device_capabilities_reject_invalid_rgbic_zone_count(zone_count):
    with pytest.raises(ValueError, match="between 1 and 12"):
        DeviceCapabilities(rgbic_zones=zone_count)
