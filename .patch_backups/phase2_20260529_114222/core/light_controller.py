"""
LightController v6 — LAN rápido, modo una/todas, discovery híbrido y capacidades.

- Hot path: UDP local fire-and-forget, coalescido a 50 ms.
- Discovery: broadcast global + directed broadcast + pywizlight opcional + scan /24 fallback.
- Targeting: modo single para una ampolleta activa o all para grupos.
- Lectura/capacidades: getPilot/getSystemConfig/getModelConfig fuera del camino caliente.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import threading
import time
from typing import Any

from config.bulbs_manager import BulbsManager
from config.controller_settings_manager import ControllerSettingsManager
from core.wiz_capabilities import Capabilities, from_wiz_config
from core.wiz_protocol import (
    WIZ_PORT,
    WizProtocol,
    create_endpoint,
    get_broadcast_addresses,
    get_lan_scan_ips,
    get_local_ip,
)

try:
    from core.pywizlight_adapter import discover_with_pywizlight
except Exception:  # pragma: no cover
    async def discover_with_pywizlight(*args, **kwargs):  # type: ignore
        return []

_LOG = logging.getLogger(__name__)


class LightController:
    MIN_INTERVAL = 0.05
    QUERY_TIMEOUT = 0.45
    MODEL_TIMEOUT = 0.30
    SCAN_TIMEOUT = 0.22
    DISCOVERY_ROUNDS = 4
    DISCOVERY_INTERVAL = 0.25
    PROBE_CONCURRENCY = 48
    SCAN_CONCURRENCY = 64

    def __init__(self, event_bus=None) -> None:
        self.event_bus = event_bus
        self.bulbs_manager = BulbsManager()
        self.settings_manager = ControllerSettingsManager()

        self.bulb_ips: set[str] = set(self.bulbs_manager.get_bulbs().keys())
        self.bulbs: dict[str, dict[str, Any]] = {}

        self.running = True
        self.loop = asyncio.new_event_loop()
        self.proto: WizProtocol | None = None
        self._scan_lock: asyncio.Lock | None = None

        self._target: dict[str, Any] = {}
        self._mirror: dict[str, Any] = {"state": True, "dimming": 100}
        self._dirty = False
        self._callback = None
        self._last_control_log = 0.0

        self._target_mode = self.settings_manager.get_target_mode()
        self._active_ip = self.settings_manager.get_active_ip()
        self._control_lock = threading.RLock()

        self.thread = threading.Thread(target=self._run_loop, daemon=True)

    # ------------------------------------------------------------------ #
    # Ciclo de vida
    # ------------------------------------------------------------------ #
    def set_callback(self, callback) -> None:
        self._callback = callback

    def start(self) -> None:
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._setup())
        self.loop.run_forever()

    async def _setup(self) -> None:
        _transport, self.proto = await create_endpoint(self.loop)
        self._scan_lock = asyncio.Lock()
        self._ensure_active_ip()
        self.loop.create_task(self._pump())
        self.loop.create_task(self._discover(aggressive=not bool(self.bulb_ips)))
        _LOG.info("[Light] Listo. Bombillas guardadas: %s", self.bulb_ips or "(ninguna)")

    def _run_coro(self, coro):
        if self.loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        return None

    # ------------------------------------------------------------------ #
    # Targeting: una ampolleta o todas
    # ------------------------------------------------------------------ #
    def _valid_ip(self, ip: str | None) -> bool:
        if not ip:
            return False
        try:
            ipaddress.ip_address(str(ip))
            return True
        except ValueError:
            return False

    def _all_known_targets(self) -> set[str]:
        targets: set[str] = set(self.bulb_ips) | set(self.bulbs.keys())
        if self.proto:
            targets |= set(self.proto.discovered.keys())
            targets |= set(self.proto.last_pilot.keys())
        return {str(ip) for ip in targets if self._valid_ip(str(ip))}

    def _live_or_discovered_targets(self) -> set[str]:
        targets: set[str] = set(self.bulbs.keys())
        if self.proto:
            targets |= set(self.proto.discovered.keys())
            targets |= set(self.proto.last_pilot.keys())
        return {str(ip) for ip in targets if self._valid_ip(str(ip))}

    def _best_active_ip(self, candidates: set[str] | None = None) -> str | None:
        candidates = set(candidates if candidates is not None else self._all_known_targets())
        if self._active_ip in candidates:
            return self._active_ip

        # Online real > discovered > saved. Esto evita mandar a IPs viejas por defecto.
        pools = [
            list(self.bulbs.keys()),
            list(self.proto.discovered.keys()) if self.proto else [],
            list(self.proto.last_pilot.keys()) if self.proto else [],
            list(self.bulb_ips),
        ]
        for pool in pools:
            for ip in sorted(pool):
                if ip in candidates and self._valid_ip(ip):
                    return str(ip)
        return sorted(candidates)[0] if candidates else None

    def _ensure_active_ip(self) -> str | None:
        ip = self._best_active_ip()
        if ip and ip != self._active_ip:
            self._active_ip = ip
            self.settings_manager.set_active_ip(ip)
        return self._active_ip

    def _control_targets(self) -> set[str]:
        known = self._all_known_targets()
        if not known:
            return set()

        if self._target_mode == "single":
            ip = self._best_active_ip(known)
            return {ip} if ip else set()

        # Modo todas: prioriza IPs vivas/descubiertas. Solo cae a guardadas si no hay nada vivo.
        live = self._live_or_discovered_targets()
        return live or known

    def get_target_config(self) -> dict[str, Any]:
        self._ensure_active_ip()
        active = self._active_ip
        active_info = self.bulbs.get(active or "", {})
        saved = self.bulbs_manager.get_bulbs()
        saved_entry = saved.get(active, {}) if isinstance(saved, dict) and active else {}
        targets = sorted(self._control_targets())
        return {
            "mode": self._target_mode,
            "active_ip": active,
            "active_name": active_info.get("name") or saved_entry.get("name") or active or "—",
            "targets": targets,
            "target_count": len(targets),
            "slider_interval_ms": self.settings_manager.get_slider_interval_ms(),
        }

    def set_target_mode(self, mode: str) -> None:
        mode = str(mode or "single").lower()
        self._target_mode = mode if mode in ("single", "all") else "single"
        self.settings_manager.set_target_mode(self._target_mode)
        self._ensure_active_ip()
        self._fire_callback()

    def set_active_bulb(self, ip: str) -> None:
        ip = (ip or "").strip()
        if not self._valid_ip(ip):
            return
        self.bulb_ips.add(ip)
        self._active_ip = ip
        self._target_mode = "single"
        self.settings_manager.set_active_ip(ip)
        self.settings_manager.set_target_mode("single")
        self._fire_callback()

    def set_slider_interval_ms(self, value: int) -> None:
        self.settings_manager.set_slider_interval_ms(value)
        self._fire_callback()

    # ------------------------------------------------------------------ #
    # Escritura coalescida
    # ------------------------------------------------------------------ #
    async def _pump(self) -> None:
        while self.running:
            if self._dirty and self.proto:
                with self._control_lock:
                    self._dirty = False
                    params = dict(self._target)
                self._broadcast(params)
                await asyncio.sleep(self.MIN_INTERVAL)
            else:
                await asyncio.sleep(0.01)

    def _broadcast(self, params: dict[str, Any]) -> None:
        if not params or not self.proto:
            return

        targets = self._control_targets()
        if not targets:
            _LOG.warning("[Light] Control ignorado: no hay targets. Params=%s", params)
            return

        for ip in sorted(targets):
            self.proto.send_pilot(ip, params)

        now = time.monotonic()
        if now - self._last_control_log > 0.8:
            _LOG.info("[Light] setPilot %s -> %s params=%s", self._target_mode, sorted(targets), params)
            self._last_control_log = now

        self._fire_callback()

    def _fire_callback(self) -> None:
        if self._callback:
            try:
                self._callback(self.get_state())
            except Exception:
                _LOG.debug("[Light] callback falló", exc_info=True)

    # ------------------------------------------------------------------ #
    # Discovery + probing
    # ------------------------------------------------------------------ #
    async def _discover(self, *, aggressive: bool = False) -> None:
        if not self.proto:
            return
        if self._scan_lock is None:
            self._scan_lock = asyncio.Lock()

        async with self._scan_lock:
            try:
                broadcasts = get_broadcast_addresses()
                local_ip = get_local_ip()
                self.proto.discovered.clear()

                pywiz_task = asyncio.create_task(discover_with_pywizlight(broadcasts, wait_time=1.25))

                for _ in range(self.DISCOVERY_ROUNDS):
                    for bcast in broadcasts:
                        self.proto.send_registration(local_ip, bcast, register=False)
                    await asyncio.sleep(self.DISCOVERY_INTERVAL)

                await asyncio.sleep(0.25)

                for item in await pywiz_task:
                    ip = item.get("ip")
                    if ip:
                        prev = self.proto.discovered.get(ip, {})
                        self.proto.discovered[ip] = {**prev, **item, "seen_at": time.time()}

                candidates = set(self.bulb_ips) | set(self.proto.discovered.keys())
                if aggressive or not candidates:
                    candidates |= await self._scan_subnet()

                self._remember_discovered_targets()
                candidates |= set(self.bulb_ips)

                await self._probe_many(candidates)
                self._ensure_active_ip()
                self._seed_mirror_from_active_or_first_live_bulb()

                _LOG.info(
                    "[Light] Discovery listo. Guardadas=%d, online=%d, destino=%s/%s",
                    len(self.bulb_ips),
                    len(self.bulbs),
                    self._target_mode,
                    self._active_ip,
                )
                self._fire_callback()
            except Exception:
                _LOG.debug("[Light] discovery falló", exc_info=True)

    async def _scan_subnet(self) -> set[str]:
        if not self.proto:
            return set()

        ips = [ip for ip in get_lan_scan_ips(limit=512) if ip not in self.bulb_ips]
        found: set[str] = set()
        sem = asyncio.Semaphore(self.SCAN_CONCURRENCY)

        async def check(ip: str) -> None:
            async with sem:
                res = await self.proto.query(ip, "getSystemConfig", self.loop, self.SCAN_TIMEOUT)
                if res and (res.get("mac") or res.get("moduleName") or res.get("fwVersion")):
                    found.add(ip)
                    prev = self.proto.discovered.get(ip, {})
                    self.proto.discovered[ip] = {
                        **prev,
                        "ip": ip,
                        "mac": res.get("mac") or prev.get("mac"),
                        "moduleName": res.get("moduleName"),
                        "source": "subnet-scan",
                        "seen_at": time.time(),
                    }

        await asyncio.gather(*(check(ip) for ip in ips), return_exceptions=True)
        return found

    def _remember_discovered_targets(self) -> None:
        if not self.proto:
            return

        saved = self.bulbs_manager.get_bulbs()
        for ip, info in list(self.proto.discovered.items()):
            if not self._valid_ip(ip):
                continue
            mac = info.get("mac")
            module = info.get("moduleName") or info.get("module")
            self.bulb_ips.add(ip)

            payload: dict[str, Any] = {"ip": ip, "mac": mac, "port": WIZ_PORT}
            if module:
                payload["module"] = module
            if isinstance(saved, dict) and ip in saved and saved[ip].get("name"):
                payload["name"] = saved[ip]["name"]
            self.bulbs_manager.add_bulb(payload)

    async def _probe_many(self, ips: set[str]) -> None:
        sem = asyncio.Semaphore(self.PROBE_CONCURRENCY)

        async def one(ip: str) -> None:
            async with sem:
                await self._probe(ip)

        await asyncio.gather(*(one(ip) for ip in sorted(ips) if self._valid_ip(ip)), return_exceptions=True)

    async def _probe(self, ip: str) -> bool:
        if not self.proto or not self._valid_ip(ip):
            return False

        sys_task = asyncio.create_task(self.proto.query(ip, "getSystemConfig", self.loop, self.QUERY_TIMEOUT))
        pilot_task = asyncio.create_task(self.proto.query(ip, "getPilot", self.loop, self.QUERY_TIMEOUT))
        sysc, pilot = await asyncio.gather(sys_task, pilot_task)

        if sysc is None and pilot is None:
            self.bulbs.pop(ip, None)
            return False

        model = None
        if sysc is not None:
            model = await self.proto.query(ip, "getModelConfig", self.loop, self.MODEL_TIMEOUT)

        discovered = self.proto.discovered.get(ip, {})
        saved = self.bulbs_manager.get_bulbs()
        saved_entry = saved.get(ip, {}) if isinstance(saved, dict) else {}

        module = (sysc or {}).get("moduleName") or discovered.get("moduleName") or saved_entry.get("module")
        mac = (sysc or {}).get("mac") or (pilot or {}).get("mac") or discovered.get("mac") or saved_entry.get("mac")
        caps = from_wiz_config(sysc, model, pilot)
        name = saved_entry.get("name")

        state = pilot or self.proto.last_pilot.get(ip, {})
        self.bulbs[ip] = {
            "ip": ip,
            "mac": mac,
            "caps": caps,
            "state": state,
            "name": name,
            "module": module,
            "system": sysc or {},
            "model": model or {},
            "rssi": state.get("rssi"),
            "last_seen": time.time(),
        }
        self.bulb_ips.add(ip)

        payload: dict[str, Any] = {"ip": ip, "mac": mac, "port": WIZ_PORT, "module": module}
        if name:
            payload["name"] = name
        self.bulbs_manager.add_bulb(payload)
        return True

    def _seed_mirror_from_active_or_first_live_bulb(self) -> None:
        candidates: list[dict[str, Any]] = []
        if self._active_ip and self._active_ip in self.bulbs:
            candidates.append(self.bulbs[self._active_ip])
        candidates.extend(info for ip, info in self.bulbs.items() if ip != self._active_ip)

        for info in candidates:
            st = info.get("state") or {}
            for key in ("state", "dimming", "temp", "sceneId", "speed", "r", "g", "b", "c", "w", "ratio"):
                if key in st:
                    self._mirror[key] = st[key]
            break

    async def _refresh_async(self) -> None:
        await self._probe_many(set(self.bulb_ips))
        self._ensure_active_ip()
        self._seed_mirror_from_active_or_first_live_bulb()
        self._fire_callback()

    def refresh(self) -> None:
        self._run_coro(self._refresh_async())

    # ------------------------------------------------------------------ #
    # Gestión de ampolletas para Ajustes
    # ------------------------------------------------------------------ #
    def rescan(self) -> None:
        self._run_coro(self._discover(aggressive=True))

    def add_bulb_manual(self, ip: str) -> None:
        ip = (ip or "").strip()
        if not self._valid_ip(ip):
            _LOG.warning("IP inválida: %s", ip)
            return

        self.bulb_ips.add(ip)
        self.bulbs_manager.add_bulb({"ip": ip, "mac": None, "port": WIZ_PORT})
        if not self._active_ip:
            self.set_active_bulb(ip)
        fut = self._run_coro(self._probe_then_notify(ip))
        if fut is None:
            self._fire_callback()

    async def _probe_then_notify(self, ip: str) -> None:
        await self._probe(ip)
        self._ensure_active_ip()
        self._fire_callback()

    def rename_bulb(self, ip: str, name: str) -> None:
        self.bulbs_manager.set_bulb_name(ip, name)
        if ip in self.bulbs:
            self.bulbs[ip]["name"] = name
        self._fire_callback()

    def remove_bulb(self, ip: str) -> None:
        self.bulb_ips.discard(ip)
        self.bulbs.pop(ip, None)
        self.bulbs_manager.remove_bulb(ip)
        if ip == self._active_ip:
            self._active_ip = None
            self.settings_manager.set_active_ip(None)
            self._ensure_active_ip()
        self._fire_callback()

    def get_bulbs_detailed(self) -> list[dict[str, Any]]:
        saved = self.bulbs_manager.get_bulbs()
        out: list[dict[str, Any]] = []

        for ip in sorted(self.bulb_ips):
            info = self.bulbs.get(ip, {})
            saved_entry = saved.get(ip, {}) if isinstance(saved, dict) else {}
            caps: Capabilities | None = info.get("caps")
            state = info.get("state") or {}
            system = info.get("system") or {}
            model = info.get("model") or {}
            cap_dict = caps.as_dict() if caps else {}
            out.append(
                {
                    "ip": ip,
                    "name": info.get("name") or saved_entry.get("name") or ip,
                    "mac": info.get("mac") or saved_entry.get("mac"),
                    "label": caps.label if caps else "—",
                    "online": ip in self.bulbs,
                    "selected": ip == self._active_ip,
                    "targeted": ip in self._control_targets(),
                    "module": info.get("module") or saved_entry.get("module"),
                    "fw_version": cap_dict.get("fw_version") or system.get("fwVersion") or model.get("fwVersion"),
                    "type_id": cap_dict.get("type_id") or system.get("typeId") or model.get("typeId"),
                    "rgb": bool(cap_dict.get("rgb")),
                    "tunable_white": bool(cap_dict.get("tunable_white")),
                    "dimmable": cap_dict.get("dimmable", True),
                    "kelvin_min": cap_dict.get("kelvin_min"),
                    "kelvin_max": cap_dict.get("kelvin_max"),
                    "rssi": state.get("rssi") or info.get("rssi"),
                    "dimming": state.get("dimming"),
                    "state": state.get("state"),
                    "temp": state.get("temp"),
                    "last_seen": info.get("last_seen"),
                }
            )
        return out

    # ------------------------------------------------------------------ #
    # API pública de control
    # ------------------------------------------------------------------ #
    def _drop_mode_keys(self, *keys: str) -> None:
        for key in keys:
            self._target.pop(key, None)
            self._mirror.pop(key, None)

    def _mark(self) -> None:
        with self._control_lock:
            self._mirror.update(self._target)
            self._dirty = True

    def set_rgb(self, r: int, g: int, b: int) -> None:
        # c/w=0 evita mezclar blanco residual con RGB saturado en algunos modelos RGB+CCT.
        r = int(max(0, min(255, r)))
        g = int(max(0, min(255, g)))
        b = int(max(0, min(255, b)))
        self._target.update({"state": True, "r": r, "g": g, "b": b, "c": 0, "w": 0})
        self._drop_mode_keys("temp", "sceneId", "speed", "cw", "ww", "temperature")
        self._mark()

    def get_kelvin_range(self, ip: str | None = None) -> tuple[int, int]:
        target_ip = ip or self._ensure_active_ip()
        if target_ip and target_ip in self.bulbs:
            caps = self.bulbs[target_ip].get("caps")
            if caps:
                return int(caps.kelvin_min), int(caps.kelvin_max)

        caps_list = [b.get("caps") for b in self.bulbs.values() if b.get("caps")]
        if caps_list:
            return min(int(c.kelvin_min) for c in caps_list), max(int(c.kelvin_max) for c in caps_list)
        return 2200, 6500

    def set_white(self, kelvin: int) -> None:
        lo, hi = self.get_kelvin_range()
        k = int(max(lo, min(hi, int(kelvin))))
        self._target.update({"state": True, "temp": k})
        self._drop_mode_keys("r", "g", "b", "c", "w", "sceneId", "speed", "cw", "ww")
        self._mark()

    def set_white_percent(self, pct: int) -> None:
        lo, hi = self.get_kelvin_range()
        p = max(0, min(100, int(pct))) / 100.0
        self.set_white(round(lo + (hi - lo) * p))

    def set_scene(self, scene_id: int, speed: int | None = None) -> None:
        self._target.update({"state": True, "sceneId": int(scene_id)})
        if speed is not None:
            self._target["speed"] = int(max(20, min(200, speed)))
        self._drop_mode_keys("r", "g", "b", "temp", "c", "w", "cw", "ww", "temperature")
        self._mark()

    def set_ratio(self, ratio: int) -> None:
        self._target["ratio"] = int(max(0, min(100, ratio)))
        self._mark()

    def set_brightness(self, pct: int) -> None:
        self._target["dimming"] = int(max(10, min(100, int(pct))))
        self._mark()

    def reset_brightness(self) -> None:
        self.set_brightness(100)

    def turn_on(self) -> None:
        self._target["state"] = True
        self._mark()

    def turn_off(self) -> None:
        self._target["state"] = False
        self._mark()

    def toggle(self) -> None:
        self.turn_off() if self._mirror.get("state", True) else self.turn_on()

    def reset_light(self) -> None:
        lo, hi = self.get_kelvin_range()
        neutral = 4000 if lo <= 4000 <= hi else round((lo + hi) / 2)
        with self._control_lock:
            self._target.clear()
            self._mirror.clear()
            self._target.update({"state": True, "dimming": 100, "temp": neutral})
            self._mirror.update(self._target)
            self._dirty = True

    def apply_favorite(self, fav: dict[str, Any]) -> None:
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "rgb":
            h = str(value).strip().lstrip("#")
            if len(h) == 6:
                self.set_rgb(*(int(h[i:i + 2], 16) for i in (0, 2, 4)))
        elif ftype == "white":
            self.set_white(int(value))
        elif ftype == "scene":
            self.set_scene(int(value))

    def get_state(self) -> dict[str, Any]:
        with self._control_lock:
            return dict(self._mirror)

    # ------------------------------------------------------------------ #
    # Capacidades agregadas para UI
    # ------------------------------------------------------------------ #
    def color_info(self) -> dict[str, Any]:
        lo, hi = self.get_kelvin_range()
        return {
            "kelvin_min": lo,
            "kelvin_max": hi,
            "supports_color": self.supports_color(),
            "supports_white": any(b.get("caps") and b["caps"].tunable_white for b in self.bulbs.values()) or not self.bulbs,
        }

    def summary(self) -> dict[str, Any]:
        caps = [b["caps"] for b in self.bulbs.values() if b.get("caps")]
        if any(c.rgb for c in caps):
            label = "RGB + Blancos"
        elif any(c.tunable_white for c in caps):
            label = "Blancos"
        elif caps:
            label = "Regulable"
        else:
            label = ""

        discovered = len(self.proto.discovered) if self.proto else 0
        target_cfg = self.get_target_config()
        return {
            "count": len(self.bulb_ips),
            "active": len(self.bulbs),
            "discovered": discovered,
            "targets": len(target_cfg.get("targets", [])),
            "target_mode": self._target_mode,
            "active_ip": target_cfg.get("active_ip"),
            "selected": target_cfg.get("active_name"),
            "label": label,
        }

    def supports_color(self) -> bool:
        ip = self._ensure_active_ip()
        if ip and ip in self.bulbs and self.bulbs[ip].get("caps"):
            return bool(self.bulbs[ip]["caps"].rgb)
        return any(b["caps"].rgb for b in self.bulbs.values() if b.get("caps")) or not self.bulbs
