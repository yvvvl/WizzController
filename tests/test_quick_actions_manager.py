from __future__ import annotations

from config.quick_actions_manager import (
    load_custom_quick_actions,
    validated_quick_action,
)


def test_quick_action_validation_rejects_unsafe_or_invalid_payloads():
    assert validated_quick_action("Desk", "rgb", "#12abef") == {
        "name": "Desk", "kind": "rgb", "value": "#12ABEF",
    }
    assert validated_quick_action("Evening", "white", "2700")["value"] == 2700
    assert validated_quick_action("Cinema", "scene", "18")["value"] == 18
    for name, kind, value in (
        ("", "on", ""), ("X" * 33, "off", ""),
        ("Color", "rgb", "#12345Z"), ("White", "white", "9999"),
        ("Bright", "brightness", "101"), ("Scene", "scene", "99999"),
        ("Unknown", "shell", "anything"),
    ):
        assert validated_quick_action(name, kind, value) is None


def test_persisted_quick_actions_are_deduplicated_and_validated():
    key = "custom:" + "a" * 32
    raw = [
        {"key": key, "name": "Sunset", "kind": "white", "value": 2700},
        {"key": key, "name": "Duplicate", "kind": "off", "value": None},
        {"key": "built-in", "name": "Invalid ID", "kind": "off", "value": None},
        {"key": "custom:" + "b" * 32, "name": "Bad", "kind": "rgb", "value": "oops"},
    ]
    assert load_custom_quick_actions(raw) == [
        {"key": key, "name": "Sunset", "kind": "white", "value": 2700},
    ]
