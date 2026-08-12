import pytest

from core.effects.models import CalibrationProfile, RGBColor, RGBICStep
from core.effects.rgbic_simulator import simulate_rgbic


def test_simulator_expands_absolute_widths_into_physical_segments():
    result = simulate_rgbic(
        [
            RGBICStep(RGBColor(255, 0, 0), width=2),
            RGBICStep(RGBColor(0, 255, 0), width=3, brightness=80),
        ],
        CalibrationProfile(physical_segments=5),
    )

    assert len(result) == 5
    assert [segment.number for segment in result] == [1, 2, 3, 4, 5]
    assert [segment.step_number for segment in result] == [1, 1, 2, 2, 2]
    assert [segment.color for segment in result] == [
        RGBColor(255, 0, 0),
        RGBColor(255, 0, 0),
        RGBColor(0, 255, 0),
        RGBColor(0, 255, 0),
        RGBColor(0, 255, 0),
    ]
    assert all(not segment.padded for segment in result)


def test_simulator_pads_uncovered_segments_with_black():
    result = simulate_rgbic(
        [RGBICStep(RGBColor(255, 0, 0), width=2)],
        CalibrationProfile(physical_segments=4),
    )

    assert [segment.color for segment in result[:2]] == [
        RGBColor(255, 0, 0),
        RGBColor(255, 0, 0),
    ]
    assert all(segment.color == RGBColor(0, 0, 0) for segment in result[2:])
    assert all(segment.padded for segment in result[2:])


def test_simulator_preserves_optional_brightness_without_modifier():
    result = simulate_rgbic(
        [
            RGBICStep(
                RGBColor(255, 0, 0),
                width=2,
                brightness=55,
            )
        ],
        CalibrationProfile(physical_segments=2),
    )

    assert [segment.brightness for segment in result] == [55, 55]


def test_simulator_rejects_widths_that_exceed_physical_segments():
    with pytest.raises(ValueError, match="cannot exceed"):
        simulate_rgbic(
            [RGBICStep(RGBColor(255, 0, 0), width=5)],
            CalibrationProfile(physical_segments=4),
        )
