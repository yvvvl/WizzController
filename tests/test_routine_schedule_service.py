from __future__ import annotations

import threading

import pytest

from config.routine_schedules_manager import RoutineSchedulesManager
from core import routine_schedule_service
from core.routine_schedule_service import (
    MissingScheduleGroup,
    save_schedule,
    start_scheduled_routine,
)

GROUP_ID = "00000000-0000-4000-8000-000000000001"


class Routines:
    def __init__(self) -> None:
        self.items = {"study": {"id": "study", "name": "Study", "actions": [{"type": "turn_on"}]}}

    def get_routine(self, uid):
        return self.items.get(uid)

    def get_routines(self):
        return list(self.items.values())

    def get_light_group(self, uid):
        return {"id": uid} if uid == GROUP_ID else None


def test_schedule_service_validates_before_persisting(tmp_path):
    store = RoutineSchedulesManager(tmp_path)
    routines = Routines()

    assert save_schedule(store, routines, "", "missing", "08:15", "[0]", "all", True) == ""
    assert store.list() == []
    with pytest.raises(MissingScheduleGroup):
        save_schedule(store, routines, "", "study", "08:15", "[0]", "group:removed", True)
    assert store.list() == []

    uid = save_schedule(store, routines, "", "study", "08:15", "[0,2]", f"group:{GROUP_ID}", True)
    assert store.list()[0]["id"] == uid
    assert store.list()[0]["target"] == f"group:{GROUP_ID}"


def test_schedule_service_dispatches_snapshot_and_reports_completion():
    routines = Routines()
    complete = threading.Event()
    results = []

    class Executor:
        def execute(self, snapshot, *, threaded, default_target):
            results.append((snapshot, threaded, default_target))

    def finished(uid, occurrence, status):
        results.append((uid, occurrence, status))
        complete.set()

    schedule = {
        "id": "scheduled", "routine_id": "study", "target": "group:desk",
        "last_occurrence": "2026-10-05T08:15",
    }
    start_scheduled_routine(schedule, routines, Executor(), finished)
    assert complete.wait(5)
    assert results == [
        ({"name": "Study", "actions": [{"type": "turn_on"}]}, False, "group:desk"),
        ("scheduled", "2026-10-05T08:15", "succeeded"),
    ]


def test_schedule_service_reports_deleted_routine():
    complete = threading.Event()
    results = []

    def finished(_uid, _occurrence, status):
        results.append(status)
        complete.set()

    start_scheduled_routine(
        {"id": "scheduled", "routine_id": "missing", "target": "all", "last_occurrence": "x"},
        Routines(), object(), finished,
    )
    assert complete.wait(5)
    assert results == ["failed: Routine was deleted"]


def test_schedule_service_reports_worker_start_failure(monkeypatch):
    class UnavailableThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            raise RuntimeError("thread unavailable")

    monkeypatch.setattr(routine_schedule_service.threading, "Thread", UnavailableThread)
    results = []
    start_scheduled_routine(
        {"id": "scheduled", "routine_id": "study", "target": "all", "last_occurrence": "x"},
        Routines(), object(), lambda _uid, _occurrence, status: results.append(status),
    )
    assert results == ["failed: worker unavailable"]
