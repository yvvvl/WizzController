from core.voice.intent_parser import VoiceIntentParser


class FakeWiz:
    pass


def action_types(intent):
    action = intent.action or {}
    if action.get("type") == "sequence":
        return [a.get("type") for a in action.get("actions", [])]
    return [action.get("type")]


def test_parse_power_off():
    intent = VoiceIntentParser(FakeWiz()).parse("pc apaga la luz")
    assert intent.ok
    assert intent.action["type"] == "method"
    assert intent.action["method"] == "turn_off"


def test_parse_color_and_brightness():
    intent = VoiceIntentParser(FakeWiz()).parse("pc pon rojo al cincuenta")
    assert intent.ok
    types = action_types(intent)
    assert "rgb" in types
    assert "brightness" in types


def test_ambiguous_color_false_positive_not_executed():
    intent = VoiceIntentParser(FakeWiz()).parse("pc pc sado")
    assert not intent.ok


def test_parse_cinema_scene():
    intent = VoiceIntentParser(FakeWiz()).parse("pese modo cine")
    assert intent.ok
    assert "scene" in action_types(intent)
