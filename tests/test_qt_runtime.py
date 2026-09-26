from PySide6.QtWidgets import QSystemTrayIcon

from qt_ui.runtime import QtDesktopRuntime


class _RuntimeSpy:
    def __init__(self) -> None:
        self.quick_panel = 0
        self.main_window = 0

    def show_quick_panel(self) -> None:
        self.quick_panel += 1

    def show_main_window(self) -> None:
        self.main_window += 1


def test_single_tray_click_opens_quick_panel():
    runtime = _RuntimeSpy()

    QtDesktopRuntime._handle_tray_activation(
        runtime, QSystemTrayIcon.ActivationReason.Trigger
    )

    assert runtime.quick_panel == 1
    assert runtime.main_window == 0


def test_double_tray_click_restores_main_window():
    runtime = _RuntimeSpy()

    QtDesktopRuntime._handle_tray_activation(
        runtime, QSystemTrayIcon.ActivationReason.DoubleClick
    )

    assert runtime.quick_panel == 0
    assert runtime.main_window == 1
