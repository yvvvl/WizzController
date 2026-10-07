from __future__ import annotations

import json
from datetime import datetime

import pytest

from config.routine_schedules_manager import RoutineSchedulesManager
from core.action_sequence import ActionSequenceExecutor
from core.local_routine_scheduler import LocalRoutineScheduler
from core.local_routine_scheduler import snapshot_scheduled_routine, validate_scheduled_routine


def test_weekly_schedule_claim_survives_restart_and_skips_missed_minutes(tmp_path):
    manager = RoutineSchedulesManager(tmp_path)
    uid = manager.upsert("", "study", "09:30", [0, 2, 4], "all", True)
    sent = []
    scheduler = LocalRoutineScheduler(manager, sent.append)
    monday = datetime(2026, 10, 5, 9, 30)
    assert scheduler.tick(datetime(2026, 10, 5, 9, 29)) == 0
    assert scheduler.tick(monday) == 1
    assert scheduler.tick(monday) == 0
    assert len(sent) == 1
    assert sent[0]["target"] == "all"

    restarted = LocalRoutineScheduler(RoutineSchedulesManager(tmp_path), sent.append)
    assert restarted.tick(monday) == 0
    assert restarted.tick(datetime(2026, 10, 5, 9, 31)) == 0
    assert restarted.tick(datetime(2026, 10, 6, 9, 30)) == 0  # Tuesday
    assert restarted.tick(datetime(2026, 10, 7, 9, 30)) == 1  # Wednesday
    assert restarted.manager.list()[0]["id"] == uid


def test_disabled_deleted_and_dst_fallback_not_replayed(tmp_path):
    manager = RoutineSchedulesManager(tmp_path)
    uid = manager.upsert("", "night", "01:30", [6], "all", True)
    dispatched = []
    scheduler = LocalRoutineScheduler(manager, dispatched.append)
    first = datetime.fromisoformat("2026-11-01T01:30:00-04:00")
    second = datetime.fromisoformat("2026-11-01T01:30:00-05:00")
    assert scheduler.tick(first) == 1
    assert scheduler.tick(second) == 0
    manager.upsert(uid, "night", "01:30", [6], "all", False)
    assert scheduler.tick(first) == 0
    manager.disable_for_routine("night")
    assert manager.list()[0]["enabled"] is False
    assert manager.delete(uid)
    assert scheduler.tick(first) == 0


@pytest.mark.parametrize("time,days,target", [
    ("24:00", [0], "all"), ("09:60", [0], "all"), ("9:30", [0], "all"),
    ("09:30", [], "all"), ("09:30", [7], "all"), ("09:30", [True], "all"),
    ("09:30", [0], "current"), ("09:30", [0], "group:bogus"),
])
def test_invalid_schedule_rejected_without_writing(tmp_path, time, days, target):
    manager = RoutineSchedulesManager(tmp_path)
    with pytest.raises(ValueError):
        manager.upsert("", "study", time, days, target, True)
    assert not manager.path.exists()


def test_corrupt_or_future_file_is_preserved(tmp_path):
    path = tmp_path / "routine_schedules.json"
    path.write_text('{"version": 99, "schedules": []}', encoding="utf-8")
    with pytest.raises(ValueError):
        RoutineSchedulesManager(tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 99


def test_duplicate_day_for_same_routine_and_target_is_rejected(tmp_path):
    manager = RoutineSchedulesManager(tmp_path)
    manager.upsert("", "study", "09:30", [0, 2], "all", True)
    with pytest.raises(ValueError, match="Overlapping"):
        manager.upsert("", "study", "09:30", [2, 4], "all", True)
    assert len(manager.list()) == 1
    assert manager.upsert("", "study", "09:30", [4], "all", True)


def test_claim_fails_closed_when_disk_write_fails(tmp_path, monkeypatch):
    manager = RoutineSchedulesManager(tmp_path)
    uid = manager.upsert("", "study", "09:30", [0], "all", True)
    def fail():
        raise OSError("disk full")
    monkeypatch.setattr(manager, "_save", fail)
    with pytest.raises(OSError):
        manager.claim(uid, "2026-10-05T09:30")
    assert manager.list()[0]["last_occurrence"] == ""


def test_scheduled_default_target_reaches_nested_actions_and_preserves_explicit_step_target():
    class Lights:
        def __init__(self):
            self.calls = []
        def apply_targeted_action(self, action, target):
            self.calls.append((action["type"], target))
            return True

    lights = Lights()
    executor = ActionSequenceExecutor(lights)
    executor.execute({"name": "Test", "actions": [
        {"type": "turn_on"}, {"type": "brightness", "value": 50, "target": "ip:192.0.2.7"},
    ]}, threaded=False, default_target="all")
    assert lights.calls == [("turn_on", "all"), ("brightness", "ip:192.0.2.7")]


def test_unavailable_scheduled_target_fails_instead_of_reporting_success():
    class Lights:
        def apply_targeted_action(self, _action, _target):
            return False

    with pytest.raises(RuntimeError, match="Destino no disponible"):
        ActionSequenceExecutor(Lights()).execute(
            {"actions": [{"type": "turn_on"}]}, threaded=False, default_target="all"
        )


def test_scheduler_rejects_steps_that_can_escape_fixed_target():
    routine = {"id": "unsafe", "actions": [{"type": "method", "method": "turn_off"}]}
    with pytest.raises(ValueError, match="Unsupported scheduled step"):
        validate_scheduled_routine(routine, lambda _uid: None)

    nested = {"id": "child", "actions": [{"type": "turn_on"}]}
    parent = {"id": "parent", "actions": [{"type": "routine", "value": "child"}]}
    validate_scheduled_routine(parent, lambda uid: nested if uid == "child" else None)
    snapshot = snapshot_scheduled_routine(parent, lambda uid: nested if uid == "child" else None)
    assert snapshot["actions"] == [{"type": "turn_on"}]
    nested["actions"].append({"type": "turn_off"})
    assert snapshot["actions"] == [{"type": "turn_on"}]
    nested["actions"] = [{"type": "routine", "value": "parent"}]
    with pytest.raises(ValueError, match="cycle"):
        validate_scheduled_routine(parent, lambda uid: {"parent": parent, "child": nested}.get(uid))
