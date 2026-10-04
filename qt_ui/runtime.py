"""Native desktop lifetime services for the official Qt shell."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QMetaObject, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QCursor, QIcon
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
        self.tray_menu: QMenu | None = None
        self._tray_menu_actions: dict[str, QAction] = {}
        self._tray_click_timer = QTimer(self)
        self._tray_click_timer.setSingleShot(True)
        self._tray_click_timer.timeout.connect(self.toggle_quick_panel)
        self._activate_requested.connect(self.show_main_window, Qt.ConnectionType.QueuedConnection)
        self._quit_requested.connect(self.quit_application, Qt.ConnectionType.QueuedConnection)
        self._create_tray(icon_path)
        language_changed = getattr(self.bridge, "languageChanged", None)
        if language_changed is not None:
            language_changed.connect(self._update_tray_menu_language)
        self.bridge.setTrayAvailable(self.tray_active)

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
        for key, callback in (
            ("main", self.show_main_window),
            ("quick_panel", self.show_quick_panel),
            ("refresh", self.bridge.refresh),
        ):
            action = QAction("", menu)
            self._connect_tray_action(action, callback)
            menu.addAction(action)
            self._tray_menu_actions[key] = action
        menu.addSeparator()
        quit_action = QAction("", menu)
        self._connect_tray_action(quit_action, self.quit_application)
        menu.addAction(quit_action)
        self._tray_menu_actions["quit"] = quit_action
        self.tray_menu = menu
        # Let the desktop environment open its own menu. In particular,
        # GNOME's AppIndicator bridge may show it on a primary click and may
        # not report Context/DoubleClick activation reasons to Qt at all.
        tray.setContextMenu(menu)
        tray.activated.connect(self._handle_tray_activation)
        tray.show()
        self.tray = tray
        self._update_tray_menu_language()

    def _connect_tray_action(self, action: QAction, callback) -> None:
        if sys.platform.startswith("linux"):
            # GNOME's AppIndicator menu is hosted outside this process. Let it
            # finish closing before a callback activates a Qt window; otherwise
            # the newly shown Quick Panel can immediately lose focus and hide.
            action.triggered.connect(
                lambda _checked=False, target=callback: QTimer.singleShot(150, target)
            )
        else:
            action.triggered.connect(callback)

    def _update_tray_menu_language(self) -> None:
        if not self._tray_menu_actions:
            return
        english = getattr(self.bridge, "language", "es") == "en"
        if self.tray is not None:
            virtual = bool(getattr(getattr(self.bridge, "controller", None), "is_virtual", False))
            if virtual:
                tooltip = ("WizZ Desktop — Virtual lights (test mode)" if english
                           else "WizZ Desktop — luces virtuales (modo de prueba)")
            else:
                tooltip = APP_NAME
            self.tray.setToolTip(tooltip)
        labels = {
            "main": ("Show WizZ Desktop", "Mostrar WizZ Desktop"),
            "quick_panel": ("Open Quick Panel", "Abrir panel rápido"),
            "refresh": ("Refresh lights", "Actualizar luces"),
            "quit": ("Quit", "Salir"),
        }
        for key, action in self._tray_menu_actions.items():
            action.setText(labels[key][0 if english else 1])

    def _handle_tray_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if sys.platform.startswith("linux"):
            # Linux tray hosts differ in which gestures they report. GNOME's
            # StatusNotifier bridge commonly provides a native menu instead
            # of reliable Trigger/DoubleClick/Context events. The menu is the
            # supported, discoverable route to the panel, app and quit actions.
            return

        # A quick panel needs to be available in one gesture while the main
        # window remains in the background.  Double click deliberately keeps
        # the conventional "restore the app" behaviour. Waiting for the
        # platform double-click interval prevents the first click of a double
        # click from also toggling the quick panel.
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if not self._tray_click_timer.isActive():
                self._schedule_tray_single_click()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._tray_click_timer.stop()
            self.toggle_main_window()
        elif reason == QSystemTrayIcon.ActivationReason.Context and self.tray_menu is not None:
            # Keep a reliable escape route on Linux: AppIndicator hosts may
            # not expose the same click gestures as Windows/macOS, but a
            # context activation should still let the user quit the app.
            self._tray_click_timer.stop()
            self.tray_menu.popup(QCursor.pos())

    def _schedule_tray_single_click(self) -> None:
        interval = 250
        try:
            interval = int(self.app.styleHints().mouseDoubleClickInterval())
        except (AttributeError, TypeError, RuntimeError):
            pass
        self._tray_click_timer.start(max(150, interval))

    def toggle_quick_panel(self) -> None:
        QMetaObject.invokeMethod(self.window, "toggleQuickPanel")

    def toggle_main_window(self) -> None:
        QMetaObject.invokeMethod(self.window, "hideQuickPanel")
        if self.window.isVisible():
            self.window.hide()
            return
        self.show_main_window()

    def show_main_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.requestActivate()

    def show_quick_panel(self) -> None:
        # Qt reports the tray icon's native screen coordinates on desktop
        # environments that expose a system-tray geometry (notably X11).
        # The bridge uses these to choose the monitor and dock edge.
        if self.tray is not None:
            geometry = self.tray.geometry()
            if geometry.isValid() and not geometry.isEmpty():
                self.bridge.setQuickPanelTrayGeometry(
                    geometry.x(), geometry.y(), geometry.width(), geometry.height()
                )
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
