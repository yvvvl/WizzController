from __future__ import annotations

from core.windows_window import WindowActivationResult
import main as app_main


class _HealthyGuard:
    def __init__(self):
        self.signals = 0

    def acquire(self):
        return False

    def owner_pid(self):
        return 4242

    def signal_existing(self):
        self.signals += 1
        return True

    def request_takeover(self):
        raise AssertionError("No debe pedir relevo si la ventana existe")

    def show_already_running_message(self):
        raise AssertionError("No debe mostrar fallback")


def test_second_launch_restores_healthy_window(monkeypatch):
    guard = _HealthyGuard()
    monkeypatch.setattr(app_main, "_INSTANCE_GUARD", guard)
    monkeypatch.setattr(
        app_main,
        "restore_window",
        lambda *args, **kwargs: WindowActivationResult(
            True,
            True,
            99,
            "restaurada",
        ),
    )

    assert app_main._acquire_or_activate_instance() is False
    assert guard.signals == 1


class _StaleGuard:
    def __init__(self):
        self.acquire_calls = 0
        self.takeover_calls = 0

    def acquire(self):
        self.acquire_calls += 1
        return self.acquire_calls >= 2

    def owner_pid(self):
        return 4343

    def signal_existing(self):
        return True

    def request_takeover(self):
        self.takeover_calls += 1
        return True

    def show_already_running_message(self):
        raise AssertionError("El relevo debe permitir continuar")


def test_stale_instance_is_replaced_after_window_timeout(monkeypatch):
    guard = _StaleGuard()
    ticks = iter([0.0, 10.0, 20.0, 21.0])

    monkeypatch.setattr(app_main, "_INSTANCE_GUARD", guard)
    monkeypatch.setattr(app_main.os, "name", "nt")
    monkeypatch.setattr(app_main.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(app_main.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        app_main,
        "restore_window",
        lambda *args, **kwargs: WindowActivationResult(
            False,
            False,
            reason="sin ventana",
        ),
    )

    assert app_main._acquire_or_activate_instance() is True
    assert guard.takeover_calls == 1
    assert guard.acquire_calls == 2


def test_registered_runtime_shutdown_runs_once(monkeypatch):
    calls = []
    monkeypatch.setattr(app_main, "_RUNTIME_SHUTDOWN_CALLBACK", None)

    app_main._register_runtime_shutdown(lambda: calls.append("stopped"))
    app_main._stop_runtime_services()
    app_main._stop_runtime_services()

    assert calls == ["stopped"]
