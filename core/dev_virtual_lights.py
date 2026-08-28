"""Development-only in-memory WiZ lights.

This module is deliberately kept outside the production transport path. It
lets a developer exercise the real desktop UI with several lights without
opening a UDP socket or writing fake devices to the user's saved-bulb list.
"""
from __future__ import annotations

import logging
import math
import os
import threading
import time
from typing import Any

from config.paths import is_flet_build
from core.light_controller import LightController
from core.wiz_capabilities import Capabilities
from core import wiz_scenes

_LOG = logging.getLogger(__name__)
ENV_NAME = "WIZZ_DEV_VIRTUAL_BULBS"
MAX_VIRTUAL_BULBS = 12


def virtual_bulb_count_from_environment() -> int:
    """Return an opt-in source-run-only simulator count, otherwise zero."""
    if is_flet_build():
        return 0
    raw = str(os.environ.get(ENV_NAME) or "").strip()
    if not raw:
        return 0
    try:
        return max(1, min(MAX_VIRTUAL_BULBS, int(raw)))
    except ValueError:
        _LOG.warning("[DEV] %s must be a number; virtual lights disabled.", ENV_NAME)
        return 0


class VirtualLightController(LightController):
    """LightController-compatible simulator with no network lifecycle."""

    is_virtual = True

    def __init__(self, count: int = 3) -> None:
        super().__init__()
        count = max(1, min(MAX_VIRTUAL_BULBS, int(count)))
        self.proto = None
        self.running = False
        self._removed_bulbs = []
        self.bulbs = {}
        self.bulb_ips = set()
        self._target_mode = "all" if count > 1 else "single"
        self._selected_ips = set()

        for index in range(count):
            ip = f"192.0.2.{10 + index}"
            self.bulb_ips.add(ip)
            self.bulbs[ip] = {
                "ip": ip,
                "mac": f"02:00:00:00:00:{index + 1:02x}",
                "name": f"Virtual bulb {index + 1}",
                "module": "DEV-RGBTW",
                "caps": Capabilities(rgb=True, tunable_white=True, dimmable=True, kelvin_min=2200, kelvin_max=6500, model="DEV-RGBTW"),
                "state": {"state": True, "dimming": 100, "temp": 4000},
                "last_seen": time.time(),
                "system": {"moduleName": "DEV-RGBTW", "fwVersion": "dev"},
                "model": {},
            }

        self._active_ip = sorted(self.bulb_ips)[0]
        self._selected_ips = set(self.bulb_ips) if count > 1 else {self._active_ip}
        self._mirror = dict(self.bulbs[self._active_ip]["state"])
        self._target = dict(self._mirror)
        self._scene_stop = threading.Event()
        self._scene_thread: threading.Thread | None = None
        self._animated_scene_targets: dict[str, dict[str, float | int]] = {}
        self._selection_change_pending = False
        _LOG.warning("[DEV] %s virtual bulbs enabled. No WiZ traffic will be sent.", count)

    def start(self) -> None:
        """Do not start the inherited event loop or UDP endpoint."""
        self.running = True
        if self._scene_thread is None or not self._scene_thread.is_alive():
            self._scene_stop.clear()
            self._scene_thread = threading.Thread(
                target=self._run_scene_animation,
                daemon=True,
                name="wizz-dev-virtual-scenes",
            )
            self._scene_thread.start()
        self._fire_callback()

    def stop(self) -> None:
        self.running = False
        self._scene_stop.set()

    def _save_control_config(self) -> None:
        """Keep simulator selections out of the user's persisted config."""

    def refresh(self) -> None:
        self._fire_callback()

    def _fire_callback(self, *, throttle: bool = False) -> None:
        """Mark target-only changes so the preview need not redraw colors."""
        if not self._selection_change_pending:
            super()._fire_callback(throttle=throttle)
            return
        if not self._callback:
            return
        snapshot = self.get_state()
        snapshot["_virtual_selection_only"] = True
        try:
            self._callback(snapshot)
        except Exception:
            _LOG.debug("[DEV] virtual selection callback failed", exc_info=True)

    def set_target_mode(self, mode: str) -> None:
        self._selection_change_pending = True
        try:
            super().set_target_mode(mode)
        finally:
            self._selection_change_pending = False

    def set_target_selection(self, ips: list[str] | set[str] | tuple[str, ...]) -> None:
        self._selection_change_pending = True
        try:
            super().set_target_selection(ips)
        finally:
            self._selection_change_pending = False

    def set_active_bulb(self, ip: str) -> None:
        self._selection_change_pending = True
        try:
            super().set_active_bulb(ip)
        finally:
            self._selection_change_pending = False

    def rescan(self) -> bool:
        self._fire_callback()
        return True

    def get_scan_status(self) -> dict[str, Any]:
        return {"in_progress": False, "found": len(self.bulbs), "error": None, "virtual": True}

    def _mark(self) -> None:
        """Apply a normal LightController command to virtual target state."""
        super()._mark()
        current = self.get_state()
        scene_id = current.get("sceneId")
        if scene_id is None:
            self._animated_scene_targets.clear()
        else:
            current["_virtual_rgb"] = self._scene_rgb(int(scene_id), 0.0)
        for ip in self._control_targets():
            info = self.bulbs.get(ip)
            if info:
                info["state"] = dict(current)
                info["last_seen"] = time.time()
        self._dirty = False
        self._fire_callback()

    def set_scene(self, scene_id: int, speed: int | None = None) -> None:
        """Apply a representative visual scene; dynamic scenes animate in DEV."""
        super().set_scene(scene_id, speed)
        scene = wiz_scenes.get(int(scene_id))
        if scene and scene.dynamic:
            scene_speed = int(speed if speed is not None else 100)
            self._animated_scene_targets = {
                ip: {
                    "scene_id": int(scene_id),
                    "speed": max(20, min(200, scene_speed)),
                    "phase": 0.0,
                    "updated_at": time.monotonic(),
                }
                for ip in self._control_targets()
            }
        else:
            self._animated_scene_targets.clear()

    @staticmethod
    def _hex_rgb(value: str) -> tuple[int, int, int]:
        clean = str(value).lstrip("#")
        if len(clean) != 6:
            return 139, 92, 246
        return tuple(int(clean[index:index + 2], 16) for index in (0, 2, 4))

    def _scene_rgb(self, scene_id: int, moment: float) -> tuple[int, int, int]:
        scene = wiz_scenes.get(scene_id)
        base = self._hex_rgb(scene.color if scene else "#8b5cf6")
        if not scene or not scene.dynamic:
            return base

        accents = {
            1: (0, 215, 255), 2: (255, 55, 120), 3: (255, 205, 80),
            4: (80, 120, 255), 5: (255, 170, 35), 7: (45, 205, 120),
            20: (255, 225, 245), 23: (0, 220, 255), 26: (255, 40, 210),
            27: (45, 205, 90), 29: (255, 210, 110), 31: (255, 180, 205),
        }
        accent = accents.get(scene_id, (255, 255, 255))
        mix = (math.sin(moment * 2.4) + 1.0) / 2.0
        return tuple(round(a + (b - a) * mix) for a, b in zip(base, accent))

    def _run_scene_animation(self) -> None:
        while not self._scene_stop.wait(0.08):
            if not self.running or not self._animated_scene_targets:
                continue
            now = time.monotonic()
            changed = False
            for ip, animation in list(self._animated_scene_targets.items()):
                scene_id = int(animation["scene_id"])
                speed = int(animation["speed"])
                info = self.bulbs.get(ip)
                if not info or info.get("state", {}).get("sceneId") != scene_id:
                    self._animated_scene_targets.pop(ip, None)
                    continue
                previous = float(animation.get("updated_at", now))
                elapsed = max(0.0, min(0.25, now - previous))
                # Higher scene speed means a quicker but still smooth fade.
                animation["phase"] = float(animation.get("phase", 0.0)) + elapsed * 2.4 * (speed / 100.0)
                animation["updated_at"] = now
                rgb = self._scene_rgb(scene_id, float(animation["phase"]))
                if info["state"].get("_virtual_rgb") != rgb:
                    info["state"]["_virtual_rgb"] = rgb
                    info["last_seen"] = time.time()
                    changed = True
            if changed:
                self._fire_callback(throttle=True)

    def reset_light(self) -> None:
        super().reset_light()
        self._mark()

    def get_virtual_bulbs(self) -> list[dict[str, Any]]:
        """Small presentation snapshot used only by the development preview."""
        return [
            {"ip": ip, "name": info.get("name", ip), "state": dict(info.get("state") or {}), "targeted": ip in self._control_targets()}
            for ip, info in sorted(self.bulbs.items())
        ]
