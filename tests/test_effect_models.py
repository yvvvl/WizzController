from dataclasses import FrozenInstanceError

import pytest

from core.effects.models import (
    CalibrationProfile,
    DeviceCapabilities,
    EffectFrame,
    RGBColor,
    RGBICFrame,
    RGBICProgram,
    RGBICStep,
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


def test_effect_frame_allows_more_than_twelve_logical_regions():
    colors = [RGBColor(index, index, index) for index in range(15)]
    zones = list(range(1, 16))

    frame = EffectFrame(
        timestamp=0,
        target="wall",
        colors=colors,
        zones=zones,
    )

    assert frame.zones == tuple(zones)


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
            "zones": [0],
        },
        {
            "timestamp": 0,
            "target": "lamp",
            "colors": [RGBColor(1, 2, 3), RGBColor(4, 5, 6)],
            "zones": [1, 1],
        },
    ],
)
def test_effect_frame_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        EffectFrame(**kwargs)


def test_rgbic_frame_allows_more_than_twelve_logical_colors():
    colors = [RGBColor(index, index + 1, index + 2) for index in range(15)]

    frame = RGBICFrame(colors=colors)

    assert len(frame.colors) == 15
    assert frame.colors[0] == RGBColor(0, 1, 2)
    assert frame.colors[-1] == RGBColor(14, 15, 16)


def test_rgbic_frame_accepts_empty_colors():
    assert RGBICFrame(colors=[]).colors == ()


def test_rgbic_frame_rejects_non_rgb_colors():
    with pytest.raises(ValueError, match="RGBColor"):
        RGBICFrame(colors=[RGBColor(1, 2, 3), "bad"])


def test_rgbic_step_accepts_optional_brightness():
    step = RGBICStep(
        color=RGBColor(1, 2, 3),
        width=2,
        brightness=75,
    )

    assert step.width == 2
    assert step.brightness == 75


@pytest.mark.parametrize("width", [0, -1, 1.5, True, "2"])
def test_rgbic_step_rejects_invalid_width(width):
    with pytest.raises(ValueError, match="positive integer"):
        RGBICStep(RGBColor(1, 2, 3), width=width)


@pytest.mark.parametrize("brightness", [-1, 101, 1.5, True, "50"])
def test_rgbic_step_rejects_invalid_brightness(brightness):
    with pytest.raises(ValueError, match="brightness must be an integer"):
        RGBICStep(
            RGBColor(1, 2, 3),
            width=1,
            brightness=brightness,
        )


def test_rgbic_program_accepts_global_modifier_and_support():
    program = RGBICProgram(
        steps=[
            RGBICStep(RGBColor(255, 0, 0), width=1),
            RGBICStep(RGBColor(0, 255, 0), width=2, brightness=40),
        ],
        modifier=100,
        support=17,
    )

    assert len(program.steps) == 2
    assert program.modifier == 100
    assert program.support == 17


@pytest.mark.parametrize("modifier", [1.5, True, "100"])
def test_rgbic_program_rejects_non_integer_modifier(modifier):
    with pytest.raises(ValueError, match="modifier must be an integer"):
        RGBICProgram(
            steps=[RGBICStep(RGBColor(1, 2, 3), width=1)],
            modifier=modifier,
            support=17,
        )


@pytest.mark.parametrize("support", [0, -1, 1.5, True, "17"])
def test_rgbic_program_rejects_invalid_support(support):
    with pytest.raises(ValueError, match="support must be a positive integer"):
        RGBICProgram(
            steps=[RGBICStep(RGBColor(1, 2, 3), width=1)],
            modifier=100,
            support=support,
        )


def test_rgbic_program_rejects_more_than_twelve_physical_steps():
    with pytest.raises(ValueError, match="between 1 and 12"):
        RGBICProgram(
            steps=[RGBICStep(RGBColor(1, 2, 3), width=1)] * 13,
            modifier=100,
            support=17,
        )


def test_calibration_profile_accepts_positive_segment_count():
    profile = CalibrationProfile(physical_segments=17)

    assert profile.physical_segments == 17


@pytest.mark.parametrize("physical_segments", [0, -1, 1.5, True, "17"])
def test_calibration_profile_rejects_invalid_segment_count(physical_segments):
    with pytest.raises(ValueError, match="positive integer"):
        CalibrationProfile(physical_segments=physical_segments)


def test_device_capabilities_use_explicit_rgbic_fields():
    capabilities = DeviceCapabilities(
        rgb=True,
        white=True,
        scenes=True,
        rgbic=True,
        rgbic_max_steps=12,
    )

    assert capabilities.rgb
    assert capabilities.white
    assert capabilities.scenes
    assert capabilities.rgbic is True
    assert capabilities.rgbic_max_steps == 12


@pytest.mark.parametrize("max_steps", [0, -1, 1.5, True])
def test_device_capabilities_reject_invalid_rgbic_max_steps(max_steps):
    with pytest.raises(ValueError, match="positive integer"):
        DeviceCapabilities(rgbic=True, rgbic_max_steps=max_steps)
