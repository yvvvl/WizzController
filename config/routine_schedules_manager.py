"""Versioned, atomic local storage for weekly routine schedules.

An occurrence is claimed on disk *before* a light command starts. This makes
restarting WizZ in the same minute safe: it cannot apply the same schedule
twice. The claim is intentionally not retried if the command subsequently
fails; a surprise late light change is worse than a missed occurrence.
"""

from __future__ import annotations

import copy
import ipaddress
import json
import os
import re
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from .paths import config_dir

_TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_MAC = re.compile(r"^mac:[0-9a-f]{12}$")
_MAX_SCHEDULES = 64


def _target(value: Any) -> str:
    target = str(value or "").strip().lower()
    if target == "all" or _MAC.fullmatch(target):
        return target
    if target.startswith("ip:"):
        try:
            return "ip:" + str(ipaddress.ip_address(target[3:]))
        except ValueError:
            pass
    if target.startswith("group:"):
        from uuid import UUID

        try:
            return "group:" + str(UUID(target[6:]))
        except ValueError:
            pass
    raise ValueError("Invalid light target")


def _days(value: Any) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError("Choose at least one weekday")
    if any(type(day) is not int or not 0 <= day <= 6 for day in value):
        raise ValueError("Weekdays must be Monday=0 through Sunday=6")
    return sorted(set(value))


class RoutineSchedulesManager:
    def __init__(self, directory: str | os.PathLike[str] | None = None) -> None:
        base = Path(directory).expanduser().resolve() if directory else config_dir()
        self.path = base / "routine_schedules.json"
        self._lock = threading.RLock()
        self.schedules: list[dict[str, Any]] = []
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("schedules"), list):
                    raise ValueError("Unsupported routine schedule file")
                if len(raw["schedules"]) > _MAX_SCHEDULES:
                    raise ValueError("Too many routine schedules")
                for row in raw["schedules"]:
                    self.schedules.append(self._validate_row(row))
                ids = [row["id"] for row in self.schedules]
                if len(ids) != len(set(ids)):
                    raise ValueError("Duplicate routine schedule ID")
                for index, left in enumerate(self.schedules):
                    for right in self.schedules[index + 1:]:
                        if (
                            left["routine_id"] == right["routine_id"]
                            and left["time"] == right["time"]
                            and left["target"] == right["target"]
                            and set(left["days"]) & set(right["days"])
                        ):
                            raise ValueError("Overlapping routine schedules")
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                # Never overwrite malformed or future-version data silently.
                raise ValueError(f"Could not load {self.path}: {exc}") from exc

    @staticmethod
    def _validate_row(row: Any) -> dict[str, Any]:
        if not isinstance(row, dict):
            raise ValueError("Invalid routine schedule")
        uid = str(row.get("id") or "")
        routine_id = str(row.get("routine_id") or "")
        if not uid or not routine_id or len(uid) > 80 or len(routine_id) > 80:
            raise ValueError("Invalid schedule or routine ID")
        time = str(row.get("time") or "")
        if not _TIME.fullmatch(time):
            raise ValueError("Time must be HH:MM (24-hour)")
        if type(row.get("enabled")) is not bool:
            raise ValueError("Invalid enabled flag")
        occurrence = str(row.get("last_occurrence") or "")
        if occurrence and not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", occurrence):
            raise ValueError("Invalid occurrence marker")
        status = str(row.get("last_status") or "")
        if len(status) > 200:
            raise ValueError("Status too long")
        return {
            "id": uid, "routine_id": routine_id, "time": time,
            "days": _days(row.get("days")), "target": _target(row.get("target")),
            "enabled": row["enabled"], "last_occurrence": occurrence,
            "last_status": status,
        }

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self.schedules)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump({"version": 1, "schedules": self.schedules}, stream, indent=2, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def upsert(self, uid: str, routine_id: str, time: str, days: list[int], target: str, enabled: bool) -> str:
        with self._lock:
            updating = bool(uid)
            uid = str(uid or uuid4())
            old = next((row for row in self.schedules if row["id"] == uid), None)
            if updating and old is None:
                raise ValueError("Schedule does not exist")
            if old is None and len(self.schedules) >= _MAX_SCHEDULES:
                raise ValueError("Schedule limit reached")
            row = self._validate_row({
                "id": uid, "routine_id": routine_id, "time": time, "days": days,
                "target": target, "enabled": enabled,
                # Editing the definition invalidates the previous occurrence;
                # toggling enabled alone does not cause a same-minute replay.
                "last_occurrence": old["last_occurrence"] if old else "",
                "last_status": old["last_status"] if old else "",
            })
            if any(
                item["id"] != uid
                and item["routine_id"] == row["routine_id"]
                and item["time"] == row["time"]
                and item["target"] == row["target"]
                and bool(set(item["days"]) & set(row["days"]))
                for item in self.schedules
            ):
                raise ValueError("Overlapping schedule for the same routine and target")
            before = self.list()
            if old is None:
                self.schedules.append(row)
            else:
                self.schedules[self.schedules.index(old)] = row
            try:
                self._save()
            except OSError:
                self.schedules = before
                raise
            return uid

    def delete(self, uid: str) -> bool:
        with self._lock:
            before = self.list()
            self.schedules = [row for row in self.schedules if row["id"] != uid]
            if len(before) == len(self.schedules):
                return False
            try:
                self._save()
            except OSError:
                self.schedules = before
                raise
            return True

    def disable_for_routine(self, routine_id: str) -> None:
        with self._lock:
            before = self.list()
            changed = False
            for row in self.schedules:
                if row["routine_id"] == routine_id and row["enabled"]:
                    row["enabled"] = False
                    row["last_status"] = "routine_deleted"
                    changed = True
            if changed:
                try:
                    self._save()
                except OSError:
                    self.schedules = before
                    raise

    def claim(self, uid: str, occurrence: str) -> dict[str, Any] | None:
        """Durably reserve one local calendar minute; return a snapshot to run."""
        with self._lock:
            row = next((item for item in self.schedules if item["id"] == uid), None)
            if row is None or not row["enabled"] or row["last_occurrence"] == occurrence:
                return None
            previous = (row["last_occurrence"], row["last_status"])
            row["last_occurrence"] = occurrence
            row["last_status"] = "running"
            try:
                self._save()
            except OSError:
                row["last_occurrence"], row["last_status"] = previous
                raise
            return copy.deepcopy(row)

    def finish(self, uid: str, occurrence: str, status: str) -> None:
        with self._lock:
            row = next((item for item in self.schedules if item["id"] == uid), None)
            if row is not None and row["last_occurrence"] == occurrence:
                previous = row["last_status"]
                row["last_status"] = status[:200]
                try:
                    self._save()
                except OSError:
                    row["last_status"] = previous
                    raise
