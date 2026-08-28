"""Linux desktop capability detection and conservative service adapters.

The adapters in this module are deliberately not wired into the application
runtime yet.  They provide a tested boundary for the Linux beta while the
Windows runtime remains unchanged.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from importlib.util import find_spec
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .capabilities import CapabilityState, DesktopCapabilities
from .contracts import SystemIntegrationService, WindowService, WorkArea


def _session_type() -> str:
    return str(os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()


def detect_linux_capabilities() -> DesktopCapabilities:
    """Describe best-effort Linux desktop support without touching hardware."""

    if not sys.platform.startswith("linux"):
        unavailable = CapabilityState.unavailable("Linux backend is not active")
        return DesktopCapabilities(
            **{name: unavailable for name in DesktopCapabilities.__dataclass_fields__}
        )

    session = _session_type()
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    xdg_open = shutil.which("xdg-open")
    tray = (
        CapabilityState.available("desktop session and pystray detected")
        if has_display
        and find_spec("pystray") is not None
        else CapabilityState.unavailable(
            "pystray is not installed" if has_display else "no graphical desktop session"
        )
    )
    # The beta intentionally has no user-safe Linux global-shortcut backend.
    # The ``keyboard`` package would require root access to /dev/input, which
    # must never be a requirement for running the desktop app.
    hotkey = CapabilityState.unavailable(
        "Linux global shortcuts are disabled until a safe XDG portal backend is implemented"
        if session == "wayland"
        else "Linux global shortcuts are not implemented in this beta"
    )
    window = (
        CapabilityState.degraded("window operations depend on the compositor")
        if has_display
        else CapabilityState.unavailable("no graphical desktop session")
    )
    return DesktopCapabilities(
        hotkey_registration=hotkey,
        hotkey_recording=hotkey,
        tray=tray,
        tray_default_action=CapabilityState.degraded("desktop menu policy varies"),
        start_at_login=CapabilityState.available("XDG autostart"),
        window_show=window,
        window_hide=window,
        window_restore=window,
        window_focus=window,
        work_area_positioning=window,
        frameless=window,
        always_on_top=window,
        taskbar_skip=window,
        single_instance_exclusion=CapabilityState.degraded("portable file lock boundary"),
        single_instance_activation=CapabilityState.unavailable(
            "activation handoff is not implemented yet"
        ),
        open_folder=(
            CapabilityState.available("xdg-open")
            if xdg_open
            else CapabilityState.unavailable("xdg-open is not installed")
        ),
    )


@dataclass(slots=True)
class LinuxAutostartService:
    """Manage one user-level XDG autostart desktop entry."""

    desktop_entry: str
    application_name: str = "WizZ Desktop"
    config_home: Path | None = None
    capabilities: DesktopCapabilities | None = None

    def __post_init__(self) -> None:
        if self.capabilities is None:
            self.capabilities = detect_linux_capabilities()

    @property
    def entry_path(self) -> Path:
        root = self.config_home or Path(
            os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        )
        return Path(root).expanduser() / "autostart" / "wizz-desktop.desktop"

    def is_enabled(self) -> bool:
        return self.entry_path.is_file()

    def set_enabled(self, enabled: bool) -> bool:
        if not self.capabilities.start_at_login.is_usable:
            return False
        path = self.entry_path
        if not enabled:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                return False
            return True
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={self.application_name}\n"
                f"Exec={self.desktop_entry}\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            path.write_text(content, encoding="utf-8")
        except OSError:
            return False
        return True


@dataclass(slots=True)
class LinuxTrayBackend:
    """Run a pystray icon without coupling the application to pystray."""

    capabilities: DesktopCapabilities | None = None
    icon_factory: Callable[[Sequence[object]], object] | None = None
    icon: object | None = None
    _thread: threading.Thread | None = None
    _running: bool = False

    def __post_init__(self) -> None:
        if self.capabilities is None:
            self.capabilities = detect_linux_capabilities()

    @property
    def running(self) -> bool:
        return self._running

    def start(self, menu: Sequence[object]) -> bool:
        if self._running or not self.capabilities.tray.is_usable:
            return False
        factory = self.icon_factory or self._default_icon
        try:
            self.icon = factory(menu)
            run_detached = getattr(self.icon, "run_detached", None)
            run = getattr(self.icon, "run")
        except (AttributeError, OSError, RuntimeError):
            self.icon = None
            return False
        if callable(run_detached):
            # GTK-based pystray backends must own their event loop; detached
            # startup avoids running GTK from an arbitrary worker thread.
            run_detached()
            self._thread = None
        else:
            self._thread = threading.Thread(
                target=self._run_icon,
                args=(run,),
                name="WizZLinuxTray",
                daemon=True,
            )
            self._thread.start()
        self._running = True
        return True

    def run_foreground(self, menu: Sequence[object]) -> bool:
        """Run the tray loop on the caller's thread.

        Linux GTK/AppIndicator backends require ownership of a toolkit event
        loop.  This explicit blocking entry point lets a future composition
        root provide that ownership without pretending that ``start`` can
        safely move the loop to an arbitrary worker thread.
        """
        if self._running or not self.capabilities.tray.is_usable:
            return False
        factory = self.icon_factory or self._default_icon
        try:
            icon = factory(menu)
            run = getattr(icon, "run")
        except (AttributeError, OSError, RuntimeError):
            return False
        self.icon = icon
        self._running = True
        try:
            run()
        except Exception:
            return False
        finally:
            self._running = False
            self.icon = None
        return True

    def update_menu(self, menu: Sequence[object]) -> bool:
        if not self._running or self.icon is None:
            return False
        try:
            setattr(self.icon, "menu", tuple(menu))
        except Exception:
            return False
        return True

    def stop(self) -> None:
        icon = self.icon
        self._running = False
        self.icon = None
        self._thread = None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass

    def _run_icon(self, run: Callable[[], object]) -> None:
        try:
            run()
        except Exception:
            self._running = False

    @staticmethod
    def _default_icon(menu: Sequence[object]) -> object:
        import pystray
        from PIL import Image

        image = Image.new("RGBA", (64, 64), (99, 102, 241, 255))
        return pystray.Icon("wizz-desktop", image, "WizZ Desktop", pystray.Menu(*menu))


@dataclass(slots=True)
class LinuxSystemIntegrationService(SystemIntegrationService):
    """Open folders through the user's XDG desktop helper."""

    capabilities: DesktopCapabilities | None = None
    runner: Callable[..., object] = subprocess.Popen

    def __post_init__(self) -> None:
        if self.capabilities is None:
            self.capabilities = detect_linux_capabilities()

    def open_folder(self, path: str | Path) -> bool:
        if not self.capabilities.open_folder.is_usable:
            return False
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return False
        try:
            self.runner(["xdg-open", str(target)])
        except OSError:
            return False
        return True


@dataclass(slots=True)
class LinuxWindowService(WindowService):
    """Callback-based window boundary for Flet/compositor-specific wiring."""

    capabilities: DesktopCapabilities
    show_callback: Callable[[], bool] | None = None
    hide_callback: Callable[[], bool] | None = None
    restore_callback: Callable[[], bool] | None = None
    focus_callback: Callable[[], bool] | None = None
    work_area: WorkArea | None = None

    def show(self) -> bool:
        return self._call(self.show_callback, "window_show")

    def hide(self) -> bool:
        return self._call(self.hide_callback, "window_hide")

    def restore(self) -> bool:
        return self._call(self.restore_callback, "window_restore")

    def focus(self) -> bool:
        return self._call(self.focus_callback, "window_focus")

    def get_work_area(self) -> WorkArea | None:
        return self.work_area if self.capabilities.work_area_positioning.is_usable else None

    def _call(self, callback: Callable[[], bool] | None, capability: str) -> bool:
        state = getattr(self.capabilities, capability)
        if not state.is_usable or callback is None:
            return False
        return bool(callback())


__all__ = [
    "LinuxAutostartService",
    "LinuxSystemIntegrationService",
    "LinuxTrayBackend",
    "LinuxWindowService",
    "detect_linux_capabilities",
]
