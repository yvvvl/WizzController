"""Application operations for local routine schedules, independent of Qt."""

from __future__ import annotations

import copy
import json
import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol

from core.local_routine_scheduler import (
    snapshot_scheduled_routine,
    validate_scheduled_routine,
)


class MissingScheduleGroup(ValueError):
    """The selected light group was removed before saving the schedule."""


class RoutineCatalog(Protocol):
    def get_routine(self, uid: str) -> dict[str, Any] | None: ...
    def get_routines(self) -> list[dict[str, Any]]: ...
    def get_light_group(self, uid: str) -> dict[str, Any] | None: ...


class ScheduleWriter(Protocol):
    def upsert(
        self, uid: str, routine_id: str, time: str, days: list[int], target: str, enabled: bool,
    ) -> str: ...


class RoutineRunner(Protocol):
    def execute(
        self, routine: dict[str, Any], *, threaded: bool, default_target: str,
    ) -> Any: ...


def save_schedule(
    schedules: ScheduleWriter,
    routines: RoutineCatalog,
    uid: str,
    routine_id: str,
    time: str,
    days_json: str,
    target: str,
    enabled: bool,
) -> str:
    """Validate references before the store writes a schedule."""
    routine = routines.get_routine(routine_id)
    if routine is None:
        return ""
    validate_scheduled_routine(routine, routines.get_routine)
    if target.startswith("group:") and not routines.get_light_group(target[6:]):
        raise MissingScheduleGroup(target[6:])
    days = json.loads(days_json)
    return schedules.upsert(uid, routine_id, time, days, target, enabled)


def start_scheduled_routine(
    schedule: dict[str, Any],
    routines: RoutineCatalog,
    executor: RoutineRunner,
    on_finished: Callable[[str, str, str], None],
) -> None:
    """Snapshot the routine before dispatch; report completion on every path.

    The callback may be a Qt signal. It must marshal delivery to the GUI
    thread; this service never touches Qt objects directly from its worker.
    """
    catalog = {
        str(routine.get("id") or ""): copy.deepcopy(routine)
        for routine in routines.get_routines()
    }
    routine = catalog.get(schedule["routine_id"])
    uid = schedule["id"]
    occurrence = schedule["last_occurrence"]
    target = schedule["target"]

    def worker() -> None:
        try:
            if routine is None:
                raise ValueError("Routine was deleted")
            snapshot = snapshot_scheduled_routine(routine, catalog.get)
            executor.execute(snapshot, threaded=False, default_target=target)
            status = "succeeded"
        except Exception as exc:
            logging.getLogger(__name__).exception("Scheduled routine %s failed", uid)
            status = "failed: " + str(exc)[:180]
        on_finished(uid, occurrence, status)

    try:
        threading.Thread(target=worker, name="wizz-routine-schedule", daemon=True).start()
    except RuntimeError as exc:
        logging.getLogger(__name__).error("Could not start scheduled routine worker: %s", exc)
        on_finished(uid, occurrence, "failed: worker unavailable")
