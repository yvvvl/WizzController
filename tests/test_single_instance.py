from __future__ import annotations

import uuid

from core.single_instance import SingleInstanceGuard


def test_single_instance_blocks_second_owner(tmp_path):
    app_id = f"WizZTest_{uuid.uuid4().hex}"
    lock_path = tmp_path / "wizz.lock"
    first = SingleInstanceGuard(app_id, lock_path=lock_path)
    second = SingleInstanceGuard(app_id, lock_path=lock_path)

    try:
        assert first.acquire() is True
        assert first.acquire() is True
        assert second.acquire() is False
    finally:
        first.close()
        second.close()

    third = SingleInstanceGuard(app_id, lock_path=lock_path)
    try:
        assert third.acquire() is True
    finally:
        third.close()


def test_close_is_idempotent(tmp_path):
    guard = SingleInstanceGuard(f"WizZTest_{uuid.uuid4().hex}", lock_path=tmp_path / "wizz.lock")
    assert guard.acquire() is True
    guard.close()
    guard.close()
    assert guard.is_owner is False


def test_owner_pid_metadata_tracks_current_owner(tmp_path):
    guard = SingleInstanceGuard(
        f"WizZTest_{uuid.uuid4().hex}",
        lock_path=tmp_path / "wizz.lock",
    )
    try:
        assert guard.acquire() is True
        assert guard.owner_pid() is not None
        assert guard.owner_pid() > 0
        assert guard.owner_path.exists()
    finally:
        guard.close()

    assert not guard.owner_path.exists()
