"""Native desktop lifetime services for the official Qt shell."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QMetaObject, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app_meta import APP_ID, APP_NAME
from config.app_runtime_manager import AppRuntimeManager
from core.single_instance import SingleInstanceGuard


class QtDesktopRuntime(QObject):
    """Own tray, close-to-tray and single-instance lifetime for Qt.

    Lighting commands remain in the bridge/controller, so hiding the main
    window does not alter device control, hotkeys or the update service.
    """

    _activate_requested = Signal()
    _quit_requested = Signal()

    def __init__(self, app: Any, window: Any, bridge: Any, settings: AppRuntimeManager,
                 guard: SingleInstanceGuard, *, icon_path: Path | None = None) -> None:
        super().__init__()
        self.app, self.window, self.bridge = app, window, bridge
        self.settings, self.guard = settings, guard
        self._quitting = False
        self.tray: QSystemTrayIcon | None = None
        self._activate_requested.connect(self.show_main_window, Qt.ConnectionType.QueuedConnection)
        self._quit_requested.connect(self.quit_application, Qt.ConnectionType.QueuedConnection)
        self._create_tray(icon_path)
        closing = getattr(self.window, "closing", None)
        if closing is not None:
            closing.connect(self._on_window_closing)

    @property
    def tray_active(self) -> bool:
        return self.tray is not None and self.tray.isVisible()

    def _create_tray(self, icon_path: Path | None) -> None:
        if not bool(self.settings.get("tray_enabled", True)):
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[QT] System tray unavailable; window close exits normally.")
            return
        icon = QIcon(str(icon_path)) if icon_path and icon_path.is_file() else QIcon()
        tray = QSystemTrayIcon(icon, self)
        tray.setToolTip(APP_NAME)
        menu = QMenu()
        for label, callback in (
            ("Show WizZ Desktop", self.show_main_window),
            ("Open Quick Panel", self.show_quick_panel),
            ("Refresh lights", self.bridge.refresh),
        ):
            action = QAction(label, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(quit_action)
        tray.setContextMenu(menu)
        tray.activated.connect(self._handle_tray_activation)
        tray.show()
        self.tray = tray

    def _on_window_closing(self, close_event: Any) -> None:
        if self._quitting or not self.tray_active or not bool(self.settings.get("minimize_to_tray", True)):
            return
        close_event.setAccepted(False)
        self.window.hide()

    def _handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_main_window()

    def show_main_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.requestActivate()

    def show_quick_panel(self) -> None:
        QMetaObject.invokeMethod(self.window, "showQuickPanel")

    def start_single_instance_listener(self) -> None:
        self.guard.start_listener(
            lambda: self._activate_requested.emit(),
            lambda: self._quit_requested.emit(),
        )

    def start_initial_visibility(self) -> None:
        if bool(self.settings.get("open_minimized", False)) and self.tray_active:
            self.window.hide()

    def quit_application(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        if self.tray is not None:
            self.tray.hide()
        self.app.quit()

    def shutdown(self) -> None:
        self._quitting = True
        if self.tray is not None:
            self.tray.hide()
        self.guard.close()


def activate_existing_instance(guard: SingleInstanceGuard) -> bool:
    """Notify the existing process without starting an unsafe duplicate."""
    return bool(guard.signal_existing() or guard.owner_pid() is not None)
