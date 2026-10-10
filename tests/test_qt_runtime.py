from types import SimpleNamespace

from PySide6.QtWidgets import QSystemTrayIcon

from qt_ui.runtime import QtDesktopRuntime, activate_existing_instance


class _RuntimeSpy:
    def __init__(self) -> None:
        self.quick_panel = 0
        self.main_window = 0
        self.tray_menu = None
        self.tray = None
        self._tray_menu_actions = {}
        self.window = _WindowSpy()
        self.bridge = _BridgeSpy()
        self.bridge.language = "es"
        self.bridge.refresh = lambda: None
        self._tray_click_timer = _TimerSpy()
        self._trigger_pair_handled = False

    def show_quick_panel(self) -> None:
        self.quick_panel += 1

    def show_main_window(self) -> None:
        self.main_window += 1

    def toggle_main_window(self) -> None:
        self.main_window += 1

    def toggle_quick_panel(self) -> None:
        self.quick_panel += 1

    def quit_application(self) -> None:
        pass

    def _update_tray_menu_language(self) -> None:
        QtDesktopRuntime._update_tray_menu_language(self)

    def _handle_tray_activation(self, reason) -> None:
        QtDesktopRuntime._handle_tray_activation(self, reason)

    def _schedule_tray_single_click(self) -> None:
        QtDesktopRuntime._schedule_tray_single_click(self)

    def _connect_tray_action(self, action, callback) -> None:
        QtDesktopRuntime._connect_tray_action(self, action, callback)


class _TimerSpy:
    def __init__(self) -> None:
        self.active = False
        self.interval = None

    def start(self, interval) -> None:
        self.active = True
        self.interval = interval

    def stop(self) -> None:
        self.active = False

    def isActive(self) -> bool:
        return self.active


class _WindowSpy:
    def __init__(self) -> None:
        self.invocations = []

    def hide(self) -> None:
        self.invocations.append("hide")

    def showMinimized(self) -> None:
        self.invocations.append("minimize")

    def setProperty(self, name, value) -> None:
        self.invocations.append((name, value))


def test_initial_visibility_respects_window_taskbar_and_tray_modes():
    for mode, tray_active, expected in (
        ("window", True, []),
        ("tray", True, ["hide"]),
        ("tray", False, [("startupMinimizing", True), "minimize"]),
    ):
        runtime = SimpleNamespace(
            settings=SimpleNamespace(get=lambda key, default: mode if key == "startup_mode" else default),
            tray_active=tray_active,
            window=_WindowSpy(),
        )
        QtDesktopRuntime.start_initial_visibility(runtime)
        assert runtime.window.invocations == expected


class _BridgeSpy:
    def __init__(self) -> None:
        self.tray_geometry = None

    def setQuickPanelTrayGeometry(self, *geometry) -> None:
        self.tray_geometry = geometry


class _TrayGeometry:
    def isValid(self) -> bool:
        return True

    def isEmpty(self) -> bool:
        return False

    def x(self) -> int:
        return 1040

    def y(self) -> int:
        return 0

    def width(self) -> int:
        return 24

    def height(self) -> int:
        return 24


class _TrayGeometryOwnerSpy:
    def geometry(self) -> _TrayGeometry:
        return _TrayGeometry()


class _QuitAppSpy:
    def __init__(self) -> None:
        self.quit_calls = 0

    def quit(self) -> None:
        self.quit_calls += 1


class _QuitRuntimeSpy:
    def __init__(self) -> None:
        self._quitting = False
        self.tray = None
        self.app = _QuitAppSpy()


class _SignalSpy:
    def connect(self, callback) -> None:
        self.callback = callback


class _ActionSpy:
    def __init__(self, label, _parent) -> None:
        self.text = label
        self.triggered = _SignalSpy()

    def setText(self, text) -> None:
        self.text = text


class _MenuActionsSpy:
    def __init__(self) -> None:
        self.actions = []

    def addAction(self, action) -> None:
        self.actions.append(action)

    def addSeparator(self) -> None:
        self.actions.append(None)


class _TrayCreationSpy:
    def __init__(self, _icon, _parent) -> None:
        self.activated = _SignalSpy()
        self.context_menu = None
        self.tooltip = None

    @staticmethod
    def isSystemTrayAvailable() -> bool:
        return True

    def setToolTip(self, tooltip) -> None:
        self.tooltip = tooltip

    def setContextMenu(self, menu) -> None:
        self.context_menu = menu

    def show(self) -> None:
        pass


def test_single_tray_click_opens_quick_panel(monkeypatch):
    monkeypatch.setattr("qt_ui.runtime.sys", SimpleNamespace(platform="win32"))
    runtime = _RuntimeSpy()

    QtDesktopRuntime._handle_tray_activation(
        runtime, QSystemTrayIcon.ActivationReason.Trigger
    )

    assert runtime.quick_panel == 0
    assert runtime.main_window == 0
    assert runtime._tray_click_timer.active
    assert runtime._tray_click_timer.interval == 250


def test_double_tray_click_toggles_main_window(monkeypatch):
    monkeypatch.setattr("qt_ui.runtime.sys", SimpleNamespace(platform="win32"))
    runtime = _RuntimeSpy()

    QtDesktopRuntime._handle_tray_activation(
        runtime, QSystemTrayIcon.ActivationReason.DoubleClick
    )

    assert runtime.quick_panel == 0
    assert runtime.main_window == 1
    assert not runtime._tray_click_timer.active


def test_linux_tray_activations_are_left_to_native_menu(monkeypatch):
    runtime = _RuntimeSpy()
    runtime.tray_menu = _MenuSpy()
    monkeypatch.setattr("qt_ui.runtime.sys", SimpleNamespace(platform="linux"))

    for reason in (
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick,
        QSystemTrayIcon.ActivationReason.Context,
    ):
        QtDesktopRuntime._handle_tray_activation(runtime, reason)

    assert runtime.main_window == 0
    assert runtime.quick_panel == 0
    assert not runtime._tray_click_timer.active
    assert runtime.tray_menu.positions == []


def test_linux_tray_attaches_localized_native_menu(monkeypatch):
    runtime = _RuntimeSpy()
    runtime.settings = type("Settings", (), {"get": lambda _self, _key, default: default})()
    menu = _MenuActionsSpy()
    monkeypatch.setattr("qt_ui.runtime.sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr("qt_ui.runtime.QSystemTrayIcon", _TrayCreationSpy)
    monkeypatch.setattr("qt_ui.runtime.QMenu", lambda: menu)
    monkeypatch.setattr("qt_ui.runtime.QAction", _ActionSpy)

    QtDesktopRuntime._create_tray(runtime, None)

    assert runtime.tray.context_menu is menu
    assert [action.text for action in menu.actions if action is not None] == [
        "Mostrar WizZ Desktop", "Abrir panel rápido", "Actualizar luces", "Salir"
    ]

    runtime.bridge.language = "en"
    QtDesktopRuntime._update_tray_menu_language(runtime)

    assert [action.text for action in menu.actions if action is not None] == [
        "Show WizZ Desktop", "Open Quick Panel", "Refresh lights", "Quit"
    ]


def test_virtual_tray_tooltip_identifies_simulator(monkeypatch):
    runtime = _RuntimeSpy()
    runtime.settings = type("Settings", (), {"get": lambda _self, _key, default: default})()
    runtime.bridge.controller = type("Controller", (), {"is_virtual": True})()
    menu = _MenuActionsSpy()
    monkeypatch.setattr("qt_ui.runtime.QSystemTrayIcon", _TrayCreationSpy)
    monkeypatch.setattr("qt_ui.runtime.QMenu", lambda: menu)
    monkeypatch.setattr("qt_ui.runtime.QAction", _ActionSpy)

    QtDesktopRuntime._create_tray(runtime, None)
    assert runtime.tray.tooltip == "WizZ Desktop — luces virtuales (modo de prueba)"

    runtime.bridge.language = "en"
    QtDesktopRuntime._update_tray_menu_language(runtime)
    assert runtime.tray.tooltip == "WizZ Desktop — Virtual lights (test mode)"


class _MenuSpy:
    def __init__(self) -> None:
        self.positions = []

    def popup(self, position) -> None:
        self.positions.append(position)


def test_opening_quick_panel_passes_native_tray_anchor(monkeypatch):
    runtime = _RuntimeSpy()
    runtime.tray = _TrayGeometryOwnerSpy()
    invoked = []
    monkeypatch.setattr(
        "qt_ui.runtime.QMetaObject.invokeMethod",
        lambda window, method: invoked.append((window, method)),
    )

    QtDesktopRuntime.show_quick_panel(runtime)

    assert runtime.bridge.tray_geometry == (1040, 0, 24, 24)
    assert invoked == [(runtime.window, "showQuickPanel")]


def test_single_tray_click_toggles_quick_panel_after_debounce(monkeypatch):
    runtime = _RuntimeSpy()
    invoked = []
    monkeypatch.setattr(
        "qt_ui.runtime.QMetaObject.invokeMethod",
        lambda window, method: invoked.append((window, method)),
    )

    QtDesktopRuntime.toggle_quick_panel(runtime)

    assert invoked == [(runtime.window, "toggleQuickPanel")]


def test_runtime_quit_bypasses_close_to_tray_behaviour():
    runtime = _QuitRuntimeSpy()

    QtDesktopRuntime.quit_application(runtime)

    assert runtime._quitting
    assert runtime.app.quit_calls == 1


def test_second_launch_signals_existing_qt_instance():
    class Guard:
        def __init__(self, signaled, owner):
            self.signaled = signaled
            self.owner = owner
            self.calls = 0

        def signal_existing(self):
            self.calls += 1
            return self.signaled

        def owner_pid(self):
            return self.owner

    for signaled, owner, expected in ((True, None, True), (False, 42, True), (False, None, False)):
        guard = Guard(signaled, owner)
        assert activate_existing_instance(guard) is expected
        assert guard.calls == 1
