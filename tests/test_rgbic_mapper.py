import pytest

from core.effects.models import CalibrationProfile, RGBColor, RGBICFrame
from core.effects.rgbic_mapper import (
    MAX_RGBIC_PHYSICAL_STEPS,
    compress_rgbic_colors,
    map_rgbic_frame,
)


def test_compression_leaves_input_unchanged_when_not_above_max_steps():
    colors = (
        RGBColor(255, 0, 0),
        RGBColor(0, 255, 0),
    )

    assert compress_rgbic_colors(colors, max_steps=MAX_RGBIC_PHYSICAL_STEPS) == colors


def test_compression_reduces_more_than_twelve_colors_and_preserves_order():
    colors = tuple(
        RGBColor(index * 10, 0, 255 - index * 10)
        for index in range(15)
    )

    compressed = compress_rgbic_colors(colors, max_steps=12)

    assert len(compressed) == 12
    assert compressed[0] == RGBColor(0, 0, 255)
    assert compressed[-1] == RGBColor(135, 0, 120)
    assert [color.red for color in compressed] == sorted(color.red for color in compressed)
    assert any(
        color.red not in {original.red for original in colors}
        for color in compressed
    )


def test_compression_averages_contiguous_groups():
    colors = (
        RGBColor(10, 0, 0),
        RGBColor(30, 0, 0),
        RGBColor(50, 0, 0),
        RGBColor(70, 0, 0),
    )

    compressed = compress_rgbic_colors(colors, max_steps=2)

    assert compressed == (
        RGBColor(20, 0, 0),
        RGBColor(60, 0, 0),
    )


def test_mapper_distributes_twelve_steps_across_seventeen_segments():
    frame = RGBICFrame(
        colors=[RGBColor(index, index + 1, index + 2) for index in range(12)]
    )

    steps = map_rgbic_frame(frame, CalibrationProfile(physical_segments=17))

    assert len(steps) == 12
    assert [step.width for step in steps] == [1, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2]
    assert sum(step.width for step in steps) == 17
    assert [step.color for step in steps] == list(frame.colors)
    assert all(step.brightness is None for step in steps)


def test_mapper_compresses_logical_colors_before_mapping_when_requested():
    colors = [RGBColor(index, 0, 0) for index in range(15)]

    compressed = compress_rgbic_colors(colors, max_steps=12)
    steps = map_rgbic_frame(
        RGBICFrame(colors=compressed),
        CalibrationProfile(physical_segments=17),
    )

    assert len(compressed) == 12
    assert len(steps) == 12
    assert sum(step.width for step in steps) == 17


def test_mapper_preserves_explicit_brightness():
    frame = RGBICFrame(
        colors=[
            RGBColor(255, 0, 0),
            RGBColor(0, 255, 0),
        ]
    )

    steps = map_rgbic_frame(
        frame,
        CalibrationProfile(physical_segments=5),
        brightness=40,
    )

    assert [step.width for step in steps] == [2, 3]
    assert all(step.brightness == 40 for step in steps)


def test_mapper_returns_no_steps_for_empty_logical_frame():
    steps = map_rgbic_frame(
        RGBICFrame(colors=[]),
        CalibrationProfile(physical_segments=9),
    )

    assert steps == ()


def test_mapper_rejects_more_logical_colors_than_physical_segments():
    frame = RGBICFrame(
        colors=[
            RGBColor(255, 0, 0),
            RGBColor(0, 255, 0),
            RGBColor(0, 0, 255),
        ]
    )

    with pytest.raises(ValueError, match="at least the logical color count"):
        map_rgbic_frame(frame, CalibrationProfile(physical_segments=2))
