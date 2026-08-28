from __future__ import annotations

import os
from typing import Any, Callable

from config.favorites_manager import FavoritesManager
from core.action_sequence import ActionSequenceExecutor


class QuickPanelController:
    """Coordinate Quick Panel state without owning WiZ protocol behavior."""

    QUICK_WIDTH = 380
    QUICK_HEIGHT = 600
    QUICK_MIN_WIDTH = 380
    QUICK_MIN_HEIGHT = 600
    QUICK_MARGIN = 16

    def __init__(
        self,
        page: Any,
        wiz: Any,
        full_app: Any,
        content_host: Any,
        *,
        favorites: Any | None = None,
        executor: Any | None = None,
        work_area_provider: Callable[
            [],
            tuple[int, int, int, int] | None,
        ]
        | None = None,
    ) -> None:
        self.page = page
        self.wiz = wiz
        self.full_app = full_app
        self.content_host = content_host
        self.favorites = favorites
        self.executor = executor or ActionSequenceExecutor(wiz)
        self.work_area_provider = (
            work_area_provider or self._system_work_area
        )
        self.view: Any | None = None
        self.window_mode = "full"
        self._full_geometry: dict[str, Any] | None = None
        self._latest_state: dict[str, Any] = {}

    def snapshot(self) -> dict[str, Any]:
        """Return a detached view model built from existing services."""

        favorites = (
            self.favorites
            if self.favorites is not None
            else FavoritesManager()
        )
        return {
            "target": dict(self.wiz.get_target_config() or {}),
            "devices": [
                dict(item)
                for item in (self.wiz.get_bulbs_detailed() or [])
                if isinstance(item, dict)
            ],
            "status": dict(self.wiz.get_tray_status() or {}),
            "favorites": [
                dict(item)
                for item in (favorites.get_favorites() or [])
                if isinstance(item, dict)
            ],
        }

    def attach_view(self, view: Any) -> None:
        self.view = view

    def refresh_view(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        update_snapshot = getattr(self.view, "update_snapshot", None)
        if callable(update_snapshot):
            update_snapshot(snapshot)
        return snapshot

    def update_state(self, state: dict[str, Any]) -> dict[str, Any] | None:
        self._latest_state = dict(state or {})
        if self.window_mode != "quick" or self.view is None:
            return None
        snapshot = self.snapshot()
        status = dict(snapshot.get("status") or {})
        status["state"] = dict(self._latest_state)
        snapshot["status"] = status
        update_snapshot = getattr(self.view, "update_snapshot", None)
        if callable(update_snapshot):
            update_snapshot(snapshot)
        return snapshot

    def select_device(self, ip: str) -> dict[str, Any]:
        self.wiz.set_active_bulb(str(ip or "").strip())
        return self.refresh_view()

    def set_target_mode(self, mode: str) -> dict[str, Any]:
        normalized = str(mode or "").strip().lower()
        if normalized not in {"single", "all"}:
            raise ValueError(f"Unsupported target mode: {mode}")
        self.wiz.set_target_mode(normalized)
        return self.refresh_view()

    def turn_on(self) -> str:
        return self.executor.execute({"type": "turn_on"}, threaded=True)

    def turn_off(self) -> str:
        return self.executor.execute({"type": "turn_off"}, threaded=True)

    def run_favorite(self, uid: str) -> str:
        return self.executor.execute(
            {"type": "favorite", "value": str(uid or "")},
            threaded=True,
        )

    def _window(self) -> Any | None:
        return getattr(self.page, "window", None)

    def _capture_full_geometry(self, window: Any) -> None:
        self._full_geometry = {
            "width": getattr(window, "width", 1080),
            "height": getattr(window, "height", 720),
            "min_width": getattr(window, "min_width", 720),
            "min_height": getattr(window, "min_height", 540),
            "resizable": getattr(window, "resizable", True),
            "maximized": getattr(window, "maximized", False),
            "full_screen": getattr(window, "full_screen", False),
            "left": getattr(window, "left", None),
            "top": getattr(window, "top", None),
            "always_on_top": getattr(window, "always_on_top", False),
            "frameless": getattr(window, "frameless", False),
            "title_bar_hidden": getattr(window, "title_bar_hidden", False),
            "title_bar_buttons_hidden": getattr(
                window,
                "title_bar_buttons_hidden",
                False,
            ),
            "maximizable": getattr(window, "maximizable", True),
            "minimizable": getattr(window, "minimizable", True),
            "shadow": getattr(window, "shadow", False),
        }

    @staticmethod
    def _cursor_monitor_work_area(
        user32: Any,
    ) -> tuple[int, int, int, int] | None:
        try:
            import ctypes
            from ctypes import wintypes

            class MonitorInfo(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                ]

            point = wintypes.POINT()
            if not user32.GetCursorPos(ctypes.byref(point)):
                return None
            monitor_from_point = user32.MonitorFromPoint
            try:
                monitor_from_point.argtypes = [
                    wintypes.POINT,
                    wintypes.DWORD,
                ]
                monitor_from_point.restype = wintypes.HANDLE
            except Exception:
                pass
            monitor = monitor_from_point(point, 1)
            if not monitor:
                return None

            info = MonitorInfo()
            info.cbSize = ctypes.sizeof(MonitorInfo)
            if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return None
            rect = info.rcWork
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return None

    @staticmethod
    def _system_work_area() -> tuple[int, int, int, int] | None:
        if os.name != "nt":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            cursor_area = QuickPanelController._cursor_monitor_work_area(
                ctypes.windll.user32,
            )
            if cursor_area is not None:
                return cursor_area

            rect = wintypes.RECT()
            spi_get_work_area = 0x0030
            ok = ctypes.windll.user32.SystemParametersInfoW(
                spi_get_work_area,
                0,
                ctypes.byref(rect),
                0,
            )
            if not ok:
                return None
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return None

    def _position_quick(self, window: Any) -> None:
        try:
            area = self.work_area_provider()
        except Exception:
            area = None
        if not area or len(area) != 4:
            return
        left, top, right, bottom = [int(value) for value in area]
        window.left = max(
            left,
            right - self.QUICK_WIDTH - self.QUICK_MARGIN,
        )
        window.top = max(
            top,
            bottom - self.QUICK_HEIGHT - self.QUICK_MARGIN,
        )

    def _update_page(self) -> bool:
        try:
            self.page.update()
            return True
        except Exception:
            return False

    def open_quick(self) -> bool:
        window = self._window()
        if window is None or self.view is None:
            return False
        if self.window_mode == "full" or self._full_geometry is None:
            self._capture_full_geometry(window)

        self.content_host.content = self.view
        window.maximized = False
        window.full_screen = False
        window.always_on_top = True
        window.frameless = True
        window.title_bar_hidden = True
        window.title_bar_buttons_hidden = True
        window.maximizable = False
        window.minimizable = False
        window.shadow = True
        window.width = self.QUICK_WIDTH
        window.height = self.QUICK_HEIGHT
        window.min_width = self.QUICK_MIN_WIDTH
        window.min_height = self.QUICK_MIN_HEIGHT
        window.resizable = False
        window.visible = True
        window.skip_task_bar = True
        window.minimized = False
        window.focused = True
        self._position_quick(window)
        self.window_mode = "quick"
        self.refresh_view()
        return self._update_page()

    def hide_quick(self) -> bool:
        window = self._window()
        if window is None:
            return False
        window.visible = False
        window.skip_task_bar = True
        self.window_mode = "hidden"
        return self._update_page()

    def open_full(self) -> bool:
        window = self._window()
        if window is None:
            return False
        was_compact = self.window_mode in {"quick", "hidden"}
        current_geometry = {
            "width": getattr(window, "width", 1080),
            "height": getattr(window, "height", 720),
            "min_width": getattr(window, "min_width", 720),
            "min_height": getattr(window, "min_height", 540),
            "resizable": getattr(window, "resizable", True),
            "maximized": getattr(window, "maximized", False),
            "full_screen": getattr(window, "full_screen", False),
            "left": getattr(window, "left", None),
            "top": getattr(window, "top", None),
            "always_on_top": getattr(window, "always_on_top", False),
            "frameless": getattr(window, "frameless", False),
            "title_bar_hidden": getattr(window, "title_bar_hidden", False),
            "title_bar_buttons_hidden": getattr(
                window,
                "title_bar_buttons_hidden",
                False,
            ),
            "maximizable": getattr(window, "maximizable", True),
            "minimizable": getattr(window, "minimizable", True),
            "shadow": getattr(window, "shadow", False),
        }
        geometry = (
            self._full_geometry or current_geometry
            if was_compact
            else current_geometry
        )
        self.content_host.content = self.full_app
        if was_compact:
            for name, value in geometry.items():
                setattr(window, name, value)
        window.visible = True
        window.skip_task_bar = False
        window.minimized = False
        window.focused = True
        self.window_mode = "full"

        set_viewport = getattr(self.full_app, "set_viewport", None)
        if callable(set_viewport):
            set_viewport(
                float(geometry["width"]),
                float(geometry["height"]),
                update=False,
            )
        return self._update_page()

    def open_full_section(self, index: int) -> bool:
        if not self.open_full():
            return False
        navigate_to = getattr(self.full_app, "navigate_to", None)
        if callable(navigate_to):
            navigate_to(int(index))
            self._update_page()
        return True

    def toggle_quick(self) -> bool:
        window = self._window()
        visible = bool(getattr(window, "visible", False)) if window is not None else False
        if self.window_mode == "quick" and visible:
            return self.hide_quick()
        return self.open_quick()


__all__ = ["QuickPanelController"]
