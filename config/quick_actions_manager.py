"""Validation and migration helpers for user-created quick actions.

The app runtime JSON owns persistence. Keep this module free of Qt so saved
actions can be checked before they are shown or sent to a light controller.
"""

from __future__ import annotations

import re
from typing import Any

from core import wiz_scenes

MAX_CUSTOM_QUICK_ACTIONS = 24
CUSTOM_KEY_PATTERN = re.compile(r"^custom:[0-9a-f]{32}$")
RGB_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
INTEGER_PATTERN = re.compile(r"^[0-9]+$")


def validated_quick_action(name: Any, kind: Any, value: Any) -> dict[str, Any] | None:
    """Return a canonical action or None; never execute unvalidated JSON."""
    title = str(name or "").strip()
    action_kind = str(kind or "").strip().lower()
    if not title or len(title) > 32:
        return None
    if action_kind in {"on", "off"}:
        normalized_value: str | int | None = None
    elif action_kind == "rgb":
        normalized_value = str(value or "").strip().upper()
        if not RGB_PATTERN.fullmatch(normalized_value):
            return None
    elif action_kind in {"white", "brightness", "scene"}:
        raw = str(value or "").strip()
        if not INTEGER_PATTERN.fullmatch(raw):
            return None
        normalized_value = int(raw)
        if action_kind == "white" and not 2200 <= normalized_value <= 6500:
            return None
        if action_kind == "brightness" and not 10 <= normalized_value <= 100:
            return None
        if action_kind == "scene" and wiz_scenes.get(normalized_value) is None:
            return None
    else:
        return None
    return {"name": title, "kind": action_kind, "value": normalized_value}


def load_custom_quick_actions(raw: Any) -> list[dict[str, Any]]:
    """Discard corrupt, duplicate or oversized persisted entries safely."""
    if not isinstance(raw, list):
        return []
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not isinstance(key, str) or not CUSTOM_KEY_PATTERN.fullmatch(key) or key in seen:
            continue
        action = validated_quick_action(item.get("name"), item.get("kind"), item.get("value"))
        if action is None:
            continue
        actions.append({"key": key, **action})
        seen.add(key)
        if len(actions) >= MAX_CUSTOM_QUICK_ACTIONS:
            break
    return actions
