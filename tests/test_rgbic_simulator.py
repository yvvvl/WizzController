from core.effects.models import RGBColor, RGBICFrame, RGBICZone
from core.effects.rgbic_simulator import simulate_rgbic


def test_simulator_represents_all_twelve_zones_without_padding():
    frame = RGBICFrame(
        zones=[
            RGBICZone(RGBColor(index, index + 1, index + 2))
            for index in range(12)
        ]
    )

    result = simulate_rgbic(frame)

    assert len(result) == 12
    assert [zone.number for zone in result] == list(range(1, 13))
    assert result[0].color == RGBColor(0, 1, 2)
    assert result[-1].color == RGBColor(11, 12, 13)
    assert all(not zone.padded for zone in result)


def test_simulator_pads_missing_zones_with_black():
    frame = RGBICFrame(
        zones=[
            RGBICZone(RGBColor(255, 0, 0)),
            RGBICZone(RGBColor(0, 255, 0)),
        ]
    )

    result = simulate_rgbic(frame)

    assert [zone.color for zone in result[:2]] == [
        RGBColor(255, 0, 0),
        RGBColor(0, 255, 0),
    ]
    assert all(zone.color == RGBColor(0, 0, 0) for zone in result[2:])
    assert all(zone.padded for zone in result[2:])


def test_simulator_represents_empty_frame_as_twelve_black_zones():
    result = simulate_rgbic(RGBICFrame(zones=[]))

    assert len(result) == 12
    assert all(zone.color == RGBColor(0, 0, 0) for zone in result)
    assert all(zone.padded for zone in result)


def test_simulator_preserves_optional_zone_weights():
    frame = RGBICFrame(
        zones=[
            RGBICZone(RGBColor(255, 0, 0), weight=3),
            RGBICZone(RGBColor(0, 255, 0)),
        ]
    )

    result = simulate_rgbic(frame)

    assert result[0].weight == 3
    assert result[1].weight is None
    assert all(zone.weight is None for zone in result[2:])
