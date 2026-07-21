from __future__ import annotations

from types import SimpleNamespace

from core.background import tray_service as tray_module
from core.background.tray_service import TrayService
from core.windows_window import WindowActivationResult


class _DeadLoop:
    def is_closed(self):
        return True

    def is_running(self):
        return False


class _Window:
    visible = False
    skip_task_bar = True
    minimized = True
    focused = False

    def to_front(self):  # pragma: no cover - fallaría el test si se invoca
        raise AssertionError("show_window no debe invocar Window.to_front()")


class _Page:
    title = "WizZ Desktop"
    window = _Window()
    session = SimpleNamespace(connection=SimpleNamespace(loop=_DeadLoop()))

    def update(self):
        raise AssertionError("No se debe actualizar una sesión cerrada")


class _Runtime:
    def get(self, key, default=None):
        return default


def test_show_window_uses_native_restore_when_flet_loop_is_closed(monkeypatch):
    calls = []

    def fake_restore(title, *, process_id=None):
        calls.append((title, process_id))
        return WindowActivationResult(True, True, 123, "restaurada")

    monkeypatch.setattr(tray_module, "restore_window", fake_restore)
    tray = TrayService(_Page(), object(), _Runtime())
    tray.last_error = None

    assert tray.show_window() is True
    assert calls and calls[0][0] == "WizZ Desktop"
    assert tray.last_error is None


def test_closed_loop_does_not_create_a_coroutine(monkeypatch):
    monkeypatch.setattr(
        tray_module,
        "restore_window",
        lambda *args, **kwargs: WindowActivationResult(
            False,
            False,
            reason="sin ventana",
        ),
    )
    tray = TrayService(_Page(), object(), _Runtime())
    created = False

    def factory():
        nonlocal created
        created = True
        raise AssertionError("No debe construirse con el loop cerrado")

    assert tray._schedule_page_coroutine(factory, label="test") is False
    assert created is False
    assert tray.show_window() is False
    assert "sin ventana" in str(tray.last_error)


def test_show_window_syncs_flet_model_on_live_loop(monkeypatch):
    import asyncio
    import threading

    loop = asyncio.new_event_loop()
    ready = threading.Event()
    updated = threading.Event()

    def run_loop():
        asyncio.set_event_loop(loop)
        ready.set()
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    assert ready.wait(1.0)

    class LiveWindow:
        visible = False
        skip_task_bar = True
        minimized = True
        focused = False

    class LivePage:
        title = "WizZ Desktop"
        window = LiveWindow()
        session = SimpleNamespace(connection=SimpleNamespace(loop=loop))

        def update(self):
            updated.set()

    monkeypatch.setattr(
        tray_module,
        "restore_window",
        lambda *args, **kwargs: WindowActivationResult(
            False,
            False,
            reason="sin ventana nativa en test",
        ),
    )

    try:
        page = LivePage()
        tray = TrayService(page, object(), _Runtime())
        assert tray.show_window() is True
        assert updated.wait(1.0)
        assert page.window.visible is True
        assert page.window.skip_task_bar is False
        assert page.window.minimized is False
        assert page.window.focused is True
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=1.0)
        loop.close()


def test_hide_window_syncs_on_live_loop(monkeypatch):
    import asyncio
    import threading

    loop = asyncio.new_event_loop()
    ready = threading.Event()
    updated = threading.Event()

    def run_loop():
        asyncio.set_event_loop(loop)
        ready.set()
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    assert ready.wait(1.0)

    class LiveWindow:
        visible = True
        skip_task_bar = False
        minimized = False
        focused = True

    class LivePage:
        title = "WizZ Desktop"
        window = LiveWindow()
        session = SimpleNamespace(connection=SimpleNamespace(loop=loop))

        def update(self):
            updated.set()

    try:
        page = LivePage()
        tray = TrayService(page, object(), _Runtime())
        tray.started = True
        tray.icon = object()

        assert tray.hide_window() is True
        assert updated.wait(1.0)
        assert page.window.visible is False
        assert page.window.skip_task_bar is True
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=1.0)
        loop.close()


def test_windows_tray_primary_action_requires_double_click(monkeypatch):
    tray = TrayService(_Page(), object(), _Runtime())
    tray._double_click_seconds = 0.5
    calls: list[bool] = []
    ticks = iter((10.0, 10.18))

    monkeypatch.setattr(tray_module.os, "name", "nt")
    monkeypatch.setattr(tray_module.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(
        tray,
        "toggle_window",
        lambda: calls.append(True) or True,
    )

    assert tray._handle_tray_primary_click() is False
    assert calls == []
    assert tray._handle_tray_primary_click() is True
    assert calls == [True]


def test_windows_tray_primary_action_resets_after_timeout(monkeypatch):
    tray = TrayService(_Page(), object(), _Runtime())
    tray._double_click_seconds = 0.4
    calls: list[bool] = []
    ticks = iter((20.0, 20.8, 21.0))

    monkeypatch.setattr(tray_module.os, "name", "nt")
    monkeypatch.setattr(tray_module.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(
        tray,
        "toggle_window",
        lambda: calls.append(True) or True,
    )

    assert tray._handle_tray_primary_click() is False
    assert tray._handle_tray_primary_click() is False
    assert calls == []
    assert tray._handle_tray_primary_click() is True
    assert calls == [True]


def test_toggle_window_hides_when_window_is_visible(monkeypatch):
    tray = TrayService(_Page(), object(), _Runtime())
    calls: list[str] = []

    monkeypatch.setattr(tray, "_window_is_visible_for_toggle", lambda: True)
    monkeypatch.setattr(tray, "hide_window", lambda: calls.append("hide") or True)
    monkeypatch.setattr(tray, "show_window", lambda: calls.append("show") or True)

    assert tray.toggle_window() is True
    assert calls == ["hide"]


def test_toggle_window_restores_when_hidden_or_minimized(monkeypatch):
    tray = TrayService(_Page(), object(), _Runtime())
    calls: list[str] = []

    monkeypatch.setattr(tray, "_window_is_visible_for_toggle", lambda: False)
    monkeypatch.setattr(tray, "hide_window", lambda: calls.append("hide") or True)
    monkeypatch.setattr(tray, "show_window", lambda: calls.append("show") or True)

    assert tray.toggle_window() is True
    assert calls == ["show"]
