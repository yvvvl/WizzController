from __future__ import annotations

from types import SimpleNamespace

import flet as ft

from core import quick_panel_controller as quick_panel_module
from core.background import tray_service as tray_module
from core.background.tray_service import TrayService
from core.quick_panel_controller import QuickPanelController
from localization import LocalizationManager
from main import _update_runtime_views
from ui.quick_panel_view import QuickPanelView


class _Window:
    width = 1080
    height = 720
    min_width = 720
    min_height = 540
    resizable = True
    visible = True
    skip_task_bar = False
    minimized = False
    focused = True
    maximized = False
    full_screen = False


class _Page:
    def __init__(self) -> None:
        self.window = _Window()
        self.update_count = 0

    def update(self) -> None:
        self.update_count += 1


class _Host:
    def __init__(self, content) -> None:
        self.content = content


class _Runtime:
    def get(self, key, default=None):
        return default


class _FullApp:
    def __init__(self) -> None:
        self.viewports: list[tuple[float, float, bool]] = []

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        self.viewports.append((width, height, update))


class _Wiz:
    def __init__(self) -> None:
        self.snapshot_reads: list[str] = []
        self.selected_ips: list[str] = []
        self.target_modes: list[str] = []
        self.active_ip = "192.168.1.20"
        self.target_mode = "single"

    def get_target_config(self) -> dict:
        self.snapshot_reads.append("target")
        targets = (
            [self.active_ip]
            if self.target_mode == "single"
            else ["192.168.1.20", "192.168.1.21"]
        )
        return {
            "mode": self.target_mode,
            "active_ip": self.active_ip,
            "targets": targets,
            "reachable": ["192.168.1.20", "192.168.1.21"],
            "saved": ["192.168.1.20", "192.168.1.21"],
        }

    def get_bulbs_detailed(self) -> list[dict]:
        self.snapshot_reads.append("devices")
        return [
            {
                "ip": "192.168.1.20",
                "name": "Living Room",
                "online": True,
                "active": self.active_ip == "192.168.1.20",
                "targeted": True,
                "state": True,
                "dimming": 72,
                "temp": None,
                "sceneId": None,
                "kelvin_min": 2200,
                "kelvin_max": 6500,
                "rgb": True,
                "tunable_white": True,
            },
            {
                "ip": "192.168.1.21",
                "name": "Bedroom",
                "online": True,
                "active": self.active_ip == "192.168.1.21",
                "targeted": self.target_mode == "all",
                "state": False,
                "dimming": 45,
                "temp": 2700,
                "sceneId": None,
                "kelvin_min": 2200,
                "kelvin_max": 6500,
                "rgb": True,
                "tunable_white": True,
            },
        ]

    def get_tray_status(self) -> dict:
        self.snapshot_reads.append("status")
        return {
            "name": "Living Room" if self.active_ip.endswith(".20") else "Bedroom",
            "ip": self.active_ip,
            "online": True,
            "mode": self.target_mode,
            "state": {"state": True, "dimming": 72},
            "summary": {"active": 2, "targets": 1},
        }

    def set_active_bulb(self, ip: str) -> None:
        self.selected_ips.append(ip)
        self.active_ip = ip
        self.target_mode = "single"

    def set_target_mode(self, mode: str) -> None:
        self.target_modes.append(mode)
        self.target_mode = mode


class _Favorites:
    def __init__(self) -> None:
        self.reads = 0
        self.items = [
            {
                "id": "fav-red",
                "name": "Red",
                "type": "rgb",
                "value": "#ff0000",
                "icon": "CIRCLE",
            },
            {
                "id": "fav-warm",
                "name": "Warm",
                "type": "white",
                "value": 2700,
                "icon": "LIGHT_MODE",
            },
        ]

    def get_favorites(self) -> list[dict]:
        self.reads += 1
        return [dict(item) for item in self.items]


class _Executor:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, bool]] = []

    def execute(self, payload: dict, threaded: bool = True) -> str:
        self.calls.append((dict(payload), threaded))
        return str(payload.get("type") or "")


def _make_controller():
    page = _Page()
    full_app = _FullApp()
    host = _Host(full_app)
    wiz = _Wiz()
    favorites = _Favorites()
    executor = _Executor()
    controller = QuickPanelController(
        page,
        wiz,
        full_app,
        host,
        favorites=favorites,
        executor=executor,
    )
    return controller, page, host, wiz, favorites, executor


def test_controller_builds_snapshot_from_existing_services() -> None:
    controller, _page, _host, wiz, favorites, _executor = _make_controller()

    snapshot = controller.snapshot()

    assert snapshot["target"]["mode"] == "single"
    assert snapshot["target"]["active_ip"] == "192.168.1.20"
    assert snapshot["devices"][0]["name"] == "Living Room"
    assert snapshot["status"]["state"]["dimming"] == 72
    assert snapshot["favorites"][0]["type"] == "rgb"
    assert wiz.snapshot_reads == ["target", "devices", "status"]
    assert favorites.reads == 1


def test_default_favorites_are_reloaded_for_each_snapshot(monkeypatch) -> None:
    first = _Favorites()
    first.items = [{"id": "first", "name": "First", "type": "rgb"}]
    second = _Favorites()
    second.items = [{"id": "second", "name": "Second", "type": "white"}]
    managers = iter((first, second))
    monkeypatch.setattr(
        quick_panel_module,
        "FavoritesManager",
        lambda: next(managers),
    )
    page = _Page()
    full_app = _FullApp()
    controller = QuickPanelController(
        page,
        _Wiz(),
        full_app,
        _Host(full_app),
        executor=_Executor(),
    )

    assert controller.snapshot()["favorites"][0]["id"] == "first"
    assert controller.snapshot()["favorites"][0]["id"] == "second"


def test_controller_merges_live_state_into_the_quick_snapshot() -> None:
    controller, _page, _host, _wiz, _favorites, _executor = _make_controller()
    snapshots: list[dict] = []
    controller.attach_view(
        SimpleNamespace(
            update_snapshot=lambda snapshot: snapshots.append(snapshot),
        )
    )
    controller.window_mode = "quick"

    snapshot = controller.update_state(
        {"state": False, "dimming": 31, "temp": 2700}
    )

    assert snapshot["status"]["state"] == {
        "state": False,
        "dimming": 31,
        "temp": 2700,
    }
    assert snapshots == [snapshot]


def test_controller_skips_compact_rebuild_while_full_app_is_active() -> None:
    controller, _page, _host, wiz, favorites, _executor = _make_controller()
    snapshots: list[dict] = []
    controller.attach_view(
        SimpleNamespace(
            update_snapshot=lambda snapshot: snapshots.append(snapshot),
        )
    )

    result = controller.update_state({"state": True, "dimming": 44})

    assert result is None
    assert snapshots == []
    assert wiz.snapshot_reads == []
    assert favorites.reads == 0


class _StateConsumer:
    def __init__(self) -> None:
        self.states: list[dict] = []

    def update_ui(self, state: dict) -> None:
        self.states.append(dict(state))

    def update_state(self, state: dict) -> None:
        self.states.append(dict(state))


def test_runtime_state_updates_full_and_quick_views() -> None:
    full = _StateConsumer()
    quick = _StateConsumer()
    state = {"state": True, "dimming": 72}

    _update_runtime_views(full, quick, state)

    assert full.states == [state]
    assert quick.states == [state]


def test_controller_selects_one_device_and_refreshes_snapshot() -> None:
    controller, _page, _host, wiz, _favorites, _executor = _make_controller()

    snapshot = controller.select_device("192.168.1.21")

    assert wiz.selected_ips == ["192.168.1.21"]
    assert snapshot["target"]["active_ip"] == "192.168.1.21"
    assert snapshot["target"]["mode"] == "single"


def test_controller_selects_all_lights_through_existing_target_api() -> None:
    controller, _page, _host, wiz, _favorites, _executor = _make_controller()

    snapshot = controller.set_target_mode("all")

    assert wiz.target_modes == ["all"]
    assert snapshot["target"]["mode"] == "all"
    assert snapshot["target"]["targets"] == [
        "192.168.1.20",
        "192.168.1.21",
    ]


def test_controller_rejects_unsupported_target_modes() -> None:
    controller, _page, _host, wiz, _favorites, _executor = _make_controller()

    try:
        controller.set_target_mode("selected")
    except ValueError as exc:
        assert str(exc) == "Unsupported target mode: selected"
    else:
        raise AssertionError("Unsupported target modes must be rejected")

    assert wiz.target_modes == []


def test_controller_routes_power_and_favorite_through_existing_executor() -> None:
    controller, _page, _host, _wiz, _favorites, executor = _make_controller()

    controller.turn_on()
    controller.turn_off()
    controller.run_favorite("fav-red")

    assert executor.calls == [
        ({"type": "turn_on"}, True),
        ({"type": "turn_off"}, True),
        ({"type": "favorite", "value": "fav-red"}, True),
    ]


def test_open_quick_reuses_window_and_replaces_only_host_content() -> None:
    controller, page, host, _wiz, _favorites, _executor = _make_controller()
    quick_view = object()
    controller.attach_view(quick_view)

    assert controller.open_quick() is True

    assert host.content is quick_view
    assert controller.window_mode == "quick"
    assert page.window.width == 430
    assert page.window.height == 720
    assert page.window.min_width == 380
    assert page.window.min_height == 520
    assert page.window.visible is True
    assert page.window.skip_task_bar is True
    assert page.update_count == 1


def test_hide_and_restore_full_app_preserve_saved_geometry() -> None:
    controller, page, host, _wiz, _favorites, _executor = _make_controller()
    controller.attach_view(object())

    controller.open_quick()
    controller.hide_quick()

    assert controller.window_mode == "hidden"
    assert page.window.visible is False
    assert page.window.skip_task_bar is True

    controller.open_full()

    assert controller.window_mode == "full"
    assert host.content is controller.full_app
    assert page.window.width == 1080
    assert page.window.height == 720
    assert page.window.min_width == 720
    assert page.window.min_height == 540
    assert page.window.resizable is True
    assert page.window.visible is True
    assert page.window.skip_task_bar is False
    assert page.window.minimized is False
    assert page.window.focused is True
    assert controller.full_app.viewports[-1] == (1080.0, 720.0, False)


def test_quick_mode_clears_and_restores_maximized_full_screen_state() -> None:
    controller, page, _host, _wiz, _favorites, _executor = _make_controller()
    controller.attach_view(object())
    page.window.maximized = True
    page.window.full_screen = True

    controller.open_quick()

    assert page.window.maximized is False
    assert page.window.full_screen is False

    controller.open_full()

    assert page.window.maximized is True
    assert page.window.full_screen is True


def test_open_full_preserves_current_geometry_when_already_in_full_mode() -> None:
    controller, page, host, _wiz, _favorites, _executor = _make_controller()
    page.window.width = 1440
    page.window.height = 900
    page.window.min_width = 760
    page.window.min_height = 560
    page.window.resizable = True
    page.window.visible = False
    controller._full_geometry = {
        "width": 1080,
        "height": 720,
        "min_width": 720,
        "min_height": 540,
        "resizable": True,
    }

    controller.open_full()

    assert host.content is controller.full_app
    assert page.window.width == 1440
    assert page.window.height == 900
    assert page.window.min_width == 760
    assert page.window.min_height == 560
    assert page.window.visible is True
    assert controller.full_app.viewports[-1] == (1440.0, 900.0, False)


def test_toggle_quick_hides_only_a_visible_quick_panel() -> None:
    controller, page, _host, _wiz, _favorites, _executor = _make_controller()
    controller.attach_view(object())

    controller.toggle_quick()
    assert controller.window_mode == "quick"

    controller.toggle_quick()
    assert controller.window_mode == "hidden"

    page.window.visible = False
    controller.toggle_quick()
    assert controller.window_mode == "quick"


class _RecordingQuickController:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def snapshot(self) -> dict:
        return {
            "target": {"mode": "single", "active_ip": None},
            "devices": [],
            "status": {"online": False, "state": {}},
            "favorites": [],
        }

    def select_device(self, ip: str) -> None:
        self.calls.append(("device", ip))

    def set_target_mode(self, mode: str) -> None:
        self.calls.append(("target", mode))

    def turn_on(self) -> None:
        self.calls.append(("power", "on"))

    def turn_off(self) -> None:
        self.calls.append(("power", "off"))

    def run_favorite(self, uid: str) -> None:
        self.calls.append(("favorite", uid))


class _Studio:
    def __init__(self) -> None:
        self.main_layout = ft.Container(data="existing-color-studio")
        self.viewports: list[tuple[float, float]] = []
        self.states: list[dict] = []
        self.languages: list[str | None] = []

    def set_viewport(self, width: float, height: float) -> None:
        self.viewports.append((width, height))

    def sync_state(self, state: dict) -> None:
        self.states.append(dict(state))

    def set_language(self, language: str | None = None) -> None:
        self.languages.append(language)
        self.main_layout = ft.Container(data=f"studio-{language}")


def _view_snapshot() -> dict:
    return {
        "target": {
            "mode": "single",
            "active_ip": "192.168.1.20",
            "targets": ["192.168.1.20"],
        },
        "devices": [
            {
                "ip": "192.168.1.20",
                "name": "Living Room",
                "online": True,
                "active": True,
                "targeted": True,
                "state": True,
                "dimming": 72,
                "temp": None,
                "sceneId": None,
            },
            {
                "ip": "192.168.1.21",
                "name": "Bedroom",
                "online": True,
                "active": False,
                "targeted": False,
                "state": False,
                "dimming": 45,
                "temp": 2700,
                "sceneId": None,
            },
        ],
        "status": {
            "name": "Living Room",
            "ip": "192.168.1.20",
            "online": True,
            "mode": "single",
            "state": {"state": True, "dimming": 72, "r": 111, "g": 130, "b": 255},
        },
        "favorites": [
            {
                "id": "fav-red",
                "name": "Red",
                "type": "rgb",
                "value": "#ff0000",
                "icon": "CIRCLE",
            },
            {
                "id": "fav-warm",
                "name": "Warm",
                "type": "white",
                "value": 2700,
                "icon": "LIGHT_MODE",
            },
            {
                "id": "fav-cinema",
                "name": "TV / Cinema",
                "type": "scene",
                "value": {"sceneId": 18, "speed": 100},
                "icon": "MOVIE",
            },
            {
                "id": "fav-dim",
                "name": "Half",
                "type": "brightness",
                "value": 50,
                "icon": "BRIGHTNESS_6",
            },
        ],
    }


def test_view_builds_compact_sections_from_i18n_and_existing_color_studio() -> None:
    i18n = LocalizationManager(preference="en")
    studio = _Studio()
    controller = _RecordingQuickController()

    view = QuickPanelView(
        controller,
        object(),
        i18n=i18n,
        color_panel=studio,
    )

    assert view.title.value == "Quick Panel"
    assert view.power_on.content == "ON"
    assert view.power_off.content == "OFF"
    assert view.color_host.content is studio.main_layout
    assert view.controls.index(view.color_host) < view.controls.index(view.favorites_section)
    assert studio.viewports == [(390, 620)]


def test_view_updates_devices_modes_status_and_favorite_callbacks() -> None:
    controller = _RecordingQuickController()
    studio = _Studio()
    view = QuickPanelView(
        controller,
        object(),
        i18n=LocalizationManager(preference="en"),
        color_panel=studio,
    )

    view.update_snapshot(_view_snapshot())

    assert [option.key for option in view.device_selector.options] == [
        "192.168.1.20",
        "192.168.1.21",
    ]
    assert view.device_selector.value == "192.168.1.20"
    assert view.online_status.value == "Online"
    assert len(view.favorite_row.controls) == 4
    assert studio.states[-1] == {
        "state": True,
        "dimming": 72,
        "r": 111,
        "g": 130,
        "b": 255,
    }

    view.device_selector.on_select(
        SimpleNamespace(control=SimpleNamespace(value="192.168.1.21"))
    )
    view.all_lights.on_click(None)
    view.power_on.on_click(None)
    view.power_off.on_click(None)
    for favorite in view.favorite_row.controls:
        favorite.on_click(None)

    assert controller.calls == [
        ("device", "192.168.1.21"),
        ("target", "all"),
        ("power", "on"),
        ("power", "off"),
        ("favorite", "fav-red"),
        ("favorite", "fav-warm"),
        ("favorite", "fav-cinema"),
        ("favorite", "fav-dim"),
    ]


def test_view_updates_all_visible_copy_through_existing_i18n() -> None:
    manager = LocalizationManager(preference="en")
    studio = _Studio()
    view = QuickPanelView(
        _RecordingQuickController(),
        object(),
        i18n=manager,
        color_panel=studio,
    )
    view.update_snapshot(_view_snapshot())

    manager.set_preference("es")

    assert view.title.value == "Panel rápido"
    assert view.online_status.value == "En línea"
    assert view.individual.content == "Una ampolleta"
    assert view.all_lights.content == "Todas las ampolletas"
    assert view.power_on.content == "ENCENDIDO"
    assert view.power_off.content == "APAGADO"
    assert view.favorites_title.value == "Favoritos"
    assert studio.languages == ["es"]
    assert view.color_host.content is studio.main_layout
    assert view.color_host.content.data == "studio-es"


class _Timer:
    instances: list["_Timer"] = []

    def __init__(self, interval, callback) -> None:
        self.interval = interval
        self.callback = callback
        self.daemon = False
        self.started = False
        self.cancelled = False
        self.instances.append(self)

    def start(self) -> None:
        self.started = True

    def cancel(self) -> None:
        self.cancelled = True


def _quick_tray(calls: list[str]) -> TrayService:
    return TrayService(
        _Page(),
        object(),
        _Runtime(),
        on_open_quick=lambda: calls.append("quick") or True,
        on_open_full=lambda: calls.append("full") or True,
        i18n=LocalizationManager(preference="en"),
    )


def test_windows_single_click_waits_then_opens_quick_panel(monkeypatch) -> None:
    calls: list[str] = []
    tray = _quick_tray(calls)
    tray._double_click_seconds = 0.5
    _Timer.instances.clear()

    monkeypatch.setattr(tray_module.os, "name", "nt")
    monkeypatch.setattr(tray_module.threading, "Timer", _Timer)

    assert tray._handle_tray_primary_click() is False
    timer = _Timer.instances[-1]
    assert timer.started is True
    assert timer.daemon is True
    assert timer.interval == 0.5
    assert calls == []

    timer.callback()

    assert calls == ["quick"]


def test_windows_double_click_cancels_quick_panel_and_opens_full_app(
    monkeypatch,
) -> None:
    calls: list[str] = []
    tray = _quick_tray(calls)
    tray._double_click_seconds = 0.5
    _Timer.instances.clear()
    ticks = iter((10.0, 10.2))

    monkeypatch.setattr(tray_module.os, "name", "nt")
    monkeypatch.setattr(tray_module.threading, "Timer", _Timer)
    monkeypatch.setattr(tray_module.time, "monotonic", lambda: next(ticks))

    assert tray._handle_tray_primary_click() is False
    timer = _Timer.instances[-1]
    assert tray._handle_tray_primary_click() is True

    assert timer.cancelled is True
    assert calls == ["full"]


def test_non_windows_primary_click_toggles_quick_panel(monkeypatch) -> None:
    calls: list[str] = []
    tray = _quick_tray(calls)

    monkeypatch.setattr(tray_module.os, "name", "posix")

    assert tray._handle_tray_primary_click() is True
    assert calls == ["quick"]


class _ClosedLoop:
    def is_closed(self) -> bool:
        return True

    def is_running(self) -> bool:
        return False


def test_tray_callback_does_not_run_on_tray_thread_after_loop_closes() -> None:
    calls: list[str] = []
    tray = _quick_tray(calls)
    tray.page.session = SimpleNamespace(
        connection=SimpleNamespace(loop=_ClosedLoop())
    )

    assert tray._open_quick_from_tray() is False
    assert calls == []


class _MenuItem:
    def __init__(self, text, action=None, **kwargs) -> None:
        self.text = text
        self.action = action
        self.kwargs = kwargs


class _Menu:
    SEPARATOR = object()

    def __new__(cls, *items):
        return list(items)


class _Pystray:
    MenuItem = _MenuItem
    Menu = _Menu


def test_tray_menu_exposes_localized_quick_and_full_actions(monkeypatch) -> None:
    calls: list[str] = []
    tray = _quick_tray(calls)
    tray._pystray = _Pystray
    monkeypatch.setattr(tray, "_scene_items", lambda **kwargs: [])
    monkeypatch.setattr(tray, "_favorite_items", lambda **kwargs: [])
    monkeypatch.setattr(tray, "_routine_items", lambda **kwargs: [])
    monkeypatch.setattr(tray, "_hotkey_menu_items", lambda: [])
    monkeypatch.setattr(tray, "_status_label", lambda: "Status")
    monkeypatch.setattr(tray, "_target_label", lambda: "Target")

    menu = tray._build_menu()
    by_text = {
        entry.text: entry
        for entry in menu
        if isinstance(entry, _MenuItem)
    }

    assert "Quick Panel" in by_text
    assert "Open WizZ Desktop" in by_text

    by_text["Quick Panel"].action(None, None)
    by_text["Open WizZ Desktop"].action(None, None)

    assert calls == ["quick", "full"]
