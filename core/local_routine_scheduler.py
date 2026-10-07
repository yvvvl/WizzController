"""Local wall-clock matching; never catches up events missed while asleep/off."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Callable

from config.routine_schedules_manager import RoutineSchedulesManager

_SAFE_STEPS = {
    "turn_on", "turn_off", "toggle", "brightness", "brightness_delta",
    "rgb", "white_kelvin", "white_percent", "scene", "wait",
}


def validate_scheduled_routine(
    routine: dict[str, Any], lookup: Callable[[str], dict[str, Any] | None],
    seen: set[str] | None = None,
) -> None:
    """Reject steps that depend on mutable UI selection or arbitrary methods."""
    seen = set(seen or ())
    uid = str(routine.get("id") or "")
    if uid in seen:
        raise ValueError("Nested routine cycle")
    seen.add(uid)
    actions = routine.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("Routine has no actions")
    for action in actions:
        kind = str(action.get("type") or "") if isinstance(action, dict) else ""
        if kind == "routine":
            nested = lookup(str(action.get("value") or action.get("id") or ""))
            if nested is None:
                raise ValueError("Nested routine not found")
            validate_scheduled_routine(nested, lookup, seen)
        elif kind not in _SAFE_STEPS:
            raise ValueError(f"Unsupported scheduled step: {kind or '<empty>'}")


def snapshot_scheduled_routine(
    routine: dict[str, Any], lookup: Callable[[str], dict[str, Any] | None],
) -> dict[str, Any]:
    """Flatten nested routines into one immutable-at-dispatch action snapshot."""
    validate_scheduled_routine(routine, lookup)

    def expand(item: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for action in item["actions"]:
            if action["type"] == "routine":
                nested = lookup(str(action.get("value") or action.get("id") or ""))
                # Validation above guarantees this lookup succeeds.
                result.extend(expand(nested))
            else:
                result.append(copy.deepcopy(action))
        return result

    return {"name": str(routine.get("name") or "Routine"), "actions": expand(routine)}


class LocalRoutineScheduler:
    def __init__(self, manager: RoutineSchedulesManager, dispatch: Callable[[dict], None]) -> None:
        self.manager = manager
        self.dispatch = dispatch

    def tick(self, now: datetime | None = None) -> int:
        now = now or datetime.now().astimezone()
        minute = now.strftime("%H:%M")
        occurrence = now.strftime("%Y-%m-%dT%H:%M")
        started = 0
        for schedule in self.manager.list():
            if schedule["enabled"] and schedule["time"] == minute and now.weekday() in schedule["days"]:
                claimed = self.manager.claim(schedule["id"], occurrence)
                if claimed is not None:
                    self.dispatch(claimed)
                    started += 1
        return started
