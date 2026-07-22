"""
LightController v8 — sync externo preciso + verificación post-acción.

- Control: UDP nativo fire-and-forget, coalescido.
- Discovery: broadcast global + broadcast por interfaz + pywizlight opcional + scan UDP /24 fallback.
- Targeting: modo single por defecto para evitar enviar a IPs viejas/offline.
- Lectura: getPilot/getSystemConfig/getModelConfig fuera del hot path.
- Sync: polling LAN liviano + verificación post-acción para reflejar cambios externos rápido.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import threading
import time
from typing import Any

from config.bulbs_manager import BulbsManager
from config.config_manager import ConfigManager
from core.wiz_capabilities import Capabilities, from_wiz_config
from core.wiz_color import (
    display_rgb_to_wiz_channels,
    logical_rgb_from_state,
    normalize_rgb,
    wiz_channels_signature,
)
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
    """Controlador principal WiZ LAN.

    El hot path no espera ACK. El estado real se refresca aparte.
    """

    MIN_INTERVAL = 0.05
    CALLBACK_MIN_INTERVAL = 0.22
    QUERY_TIMEOUT = 0.45
    MODEL_TIMEOUT = 0.30
    STATE_SYNC_TIMEOUT = 0.18
    POST_ACTION_VERIFY_DELAYS = (0.12, 0.40)
    SCAN_TIMEOUT = 0.22
    PYWIZ_DISCOVERY_TIMEOUT = 3.5
    SUBNET_SCAN_TIMEOUT = 7.0
    DISCOVERY_ROUNDS = 4
    DISCOVERY_INTERVAL = 0.25
    PROBE_CONCURRENCY = 48
    SCAN_CONCURRENCY = 64

    def __init__(self, event_bus=None) -> None:
        self.event_bus = event_bus
        self.bulbs_manager = BulbsManager()
        self.config = ConfigManager()

        self.bulb_ips: set[str] = set(self.bulbs_manager.get_bulbs().keys())
        self.bulbs: dict[str, dict[str, Any]] = {}

        self.running = True
        self.loop = asyncio.new_event_loop()
        self.proto: WizProtocol | None = None
        self._scan_lock: asyncio.Lock | None = None
        self._scan_state_lock = threading.RLock()
        self._scan_in_progress = False
        self._scan_started_at = 0.0
        self._scan_finished_at = 0.0
        self._scan_last_error: str | None = None
        self._scan_last_found = 0

        # Una eliminación explícita crea una pequeña lápida persistente. Así la
        # ampolleta no reaparece por caches UDP o por el discovery automático al
        # reiniciar. «Buscar ampolletas» limpia estas lápidas deliberadamente.
        self._removed_lock = threading.RLock()
        self._removed_bulbs = self._load_removed_bulbs()

        control_cfg = self.config.get("control", {}) or {}
        self._target_mode = self._normalise_mode(control_cfg.get("mode", "single"))
        self._active_ip = control_cfg.get("active_ip")
        try:
            self._slider_interval_ms = int(control_cfg.get("slider_interval_ms", 65))
        except Exception:
            self._slider_interval_ms = 65
        self._slider_interval_ms = max(35, min(200, self._slider_interval_ms))
        self.MIN_INTERVAL = self._slider_interval_ms / 1000.0

        sync_cfg = self.config.get("state_sync", {}) or {}
        self._state_sync_enabled = bool(sync_cfg.get("enabled", True))
        try:
            self._state_sync_interval_s = float(sync_cfg.get("interval_s", 0.35))
        except Exception:
            self._state_sync_interval_s = 0.35
        self._state_sync_interval_s = max(0.25, min(10.0, self._state_sync_interval_s))
        try:
            self._state_sync_max_targets = int(sync_cfg.get("max_targets", 1))
        except Exception:
            self._state_sync_max_targets = 1
        self._state_sync_max_targets = max(1, min(12, self._state_sync_max_targets))
        self._last_state_signature: dict[str, tuple] = {}
        self._last_state_sync_log = 0.0
        self._last_successful_sync_at = 0.0
        self._last_control_at = 0.0
        self._sync_boost_until = 0.0

        self._target: dict[str, Any] = {}
        self._mirror: dict[str, Any] = {"state": True, "dimming": 100}
        self._dirty = False
        self._callback = None
        self._last_control_log = 0.0
        self._last_callback_log = 0.0

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
        self.loop.create_task(self._pump())
        self.loop.create_task(self._state_sync_loop())
        if self._claim_scan(explicit=False):
            self.loop.create_task(
                self._discover(
                    aggressive=not bool(self.bulb_ips),
                    scan_claimed=True,
                )
            )
        _LOG.info("[Light] Listo. Bombillas guardadas: %s", self.bulb_ips or "(ninguna)")

    def _run_coro(self, coro):
        if self.loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        # Evita warnings de «coroutine was never awaited» si una acción llega
        # durante el cierre o antes de que el loop haya arrancado.
        try:
            coro.close()
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------ #
    # Eliminación persistente + estado de discovery
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalise_mac(value: Any) -> str | None:
        clean = "".join(
            ch for ch in str(value or "").lower()
            if ch in "0123456789abcdef"
        )
        return clean or None

    def _load_removed_bulbs(self) -> list[dict[str, str]]:
        raw = self.config.get("removed_bulbs", [])
        if isinstance(raw, dict):
            raw = list(raw.values())
        if not isinstance(raw, list):
            return []

        out: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in raw:
            if isinstance(item, str):
                item = {"ip": item}
            if not isinstance(item, dict):
                continue
            ip = str(item.get("ip") or "").strip()
            mac = self._normalise_mac(item.get("mac")) or ""
            if not ip and not mac:
                continue
            key = (ip, mac)
            if key in seen:
                continue
            seen.add(key)
            entry: dict[str, str] = {}
            if ip:
                entry["ip"] = ip
            if mac:
                entry["mac"] = mac
            out.append(entry)
        return out[-64:]

    def _save_removed_bulbs(self) -> None:
        with self._removed_lock:
            payload = [dict(item) for item in self._removed_bulbs[-64:]]
        self.config.set("removed_bulbs", payload)

    def _is_removed_bulb(self, ip: str | None, mac: Any = None) -> bool:
        clean_ip = str(ip or "").strip()
        clean_mac = self._normalise_mac(mac)
        with self._removed_lock:
            for entry in self._removed_bulbs:
                if clean_ip and entry.get("ip") == clean_ip:
                    return True
                if clean_mac and entry.get("mac") == clean_mac:
                    return True
        return False

    def _remember_removed_bulb(self, ip: str, mac: Any = None) -> None:
        clean_ip = str(ip or "").strip()
        clean_mac = self._normalise_mac(mac)
        if not clean_ip and not clean_mac:
            return
        with self._removed_lock:
            self._removed_bulbs = [
                entry
                for entry in self._removed_bulbs
                if not (
                    (clean_ip and entry.get("ip") == clean_ip)
                    or (clean_mac and entry.get("mac") == clean_mac)
                )
            ]
            entry: dict[str, str] = {}
            if clean_ip:
                entry["ip"] = clean_ip
            if clean_mac:
                entry["mac"] = clean_mac
            self._removed_bulbs.append(entry)
        self._save_removed_bulbs()

    def _forget_removed_bulb(self, ip: str | None = None, mac: Any = None) -> bool:
        clean_ip = str(ip or "").strip()
        clean_mac = self._normalise_mac(mac)
        with self._removed_lock:
            before = len(self._removed_bulbs)
            self._removed_bulbs = [
                entry
                for entry in self._removed_bulbs
                if not (
                    (clean_ip and entry.get("ip") == clean_ip)
                    or (clean_mac and entry.get("mac") == clean_mac)
                )
            ]
            changed = len(self._removed_bulbs) != before
        if changed:
            self._save_removed_bulbs()
        return changed

    def _clear_removed_bulbs(self) -> bool:
        with self._removed_lock:
            if not self._removed_bulbs:
                return False
            self._removed_bulbs = []
        self._save_removed_bulbs()
        return True

    def _device_mac(self, ip: str) -> Any:
        live = self.bulbs.get(ip, {})
        if live.get("mac"):
            return live.get("mac")
        if self.proto:
            discovered = self.proto.discovered.get(ip, {})
            if discovered.get("mac"):
                return discovered.get("mac")
        saved = self.bulbs_manager.get_bulbs()
        if isinstance(saved, dict):
            entry = saved.get(ip, {})
            if isinstance(entry, dict):
                return entry.get("mac")
        return None

    def _purge_device_cache(self, ip: str) -> None:
        self.bulb_ips.discard(ip)
        self.bulbs.pop(ip, None)
        self._last_state_signature.pop(ip, None)
        if self.proto:
            self.proto.discovered.pop(ip, None)
            self.proto.last_pilot.pop(ip, None)

    def _prune_removed_protocol_cache(self) -> None:
        """Purga respuestas tard?as de dispositivos expl?citamente quitados."""

        if not self.proto:
            return

        candidates = (
            set(self.proto.discovered.keys())
            | set(self.proto.last_pilot.keys())
        )

        for ip in list(candidates):
            discovered = self.proto.discovered.get(ip, {})
            pilot = self.proto.last_pilot.get(ip, {})

            discovered_mac = (
                discovered.get("mac")
                if isinstance(discovered, dict)
                else None
            )
            pilot_mac = (
                pilot.get("mac")
                if isinstance(pilot, dict)
                else None
            )

            if self._is_removed_bulb(
                ip,
                discovered_mac or pilot_mac,
            ):
                self._purge_device_cache(ip)

    def _claim_scan(self, *, explicit: bool) -> bool:
        with self._scan_state_lock:
            if self._scan_in_progress:
                return False
            self._scan_in_progress = True
            self._scan_started_at = time.time()
            self._scan_last_error = None
        if explicit:
            # Una búsqueda explícita significa «quiero volver a detectar todo»,
            # incluyendo dispositivos que antes quité de la lista.
            self._clear_removed_bulbs()
        self._fire_callback()
        return True

    def _finish_scan(self, error: str | None = None) -> None:
        with self._scan_state_lock:
            self._scan_in_progress = False
            self._scan_finished_at = time.time()
            self._scan_last_error = str(error) if error else None
            self._scan_last_found = len(self.bulbs)
        self._fire_callback()

    def get_scan_status(self) -> dict[str, Any]:
        with self._scan_state_lock:
            return {
                "running": self._scan_in_progress,
                "started_at": self._scan_started_at,
                "finished_at": self._scan_finished_at,
                "error": self._scan_last_error,
                "found": self._scan_last_found,
            }

    # ------------------------------------------------------------------ #
    # Targeting: una ampolleta / todas
    # ------------------------------------------------------------------ #
    def _normalise_mode(self, mode: Any) -> str:
        m = str(mode or "single").lower().strip()
        return "all" if m in {"all", "multi", "group", "todas"} else "single"

    def _save_control_config(self) -> None:
        self.config.set(
            "control",
            {
                "mode": self._target_mode,
                "active_ip": self._active_ip,
                "slider_interval_ms": self._slider_interval_ms,
            },
        )

    def _save_state_sync_config(self) -> None:
        self.config.set(
            "state_sync",
            {
                "enabled": self._state_sync_enabled,
                "interval_s": self._state_sync_interval_s,
                "max_targets": self._state_sync_max_targets,
            },
        )

    def set_state_sync(self, enabled: bool | None = None, interval_s: float | None = None) -> None:
        if enabled is not None:
            self._state_sync_enabled = bool(enabled)
        if interval_s is not None:
            try:
                self._state_sync_interval_s = max(0.25, min(10.0, float(interval_s)))
            except Exception:
                pass
        self._save_state_sync_config()
        self._fire_callback()

    def get_state_sync_config(self) -> dict[str, Any]:
        return {
            "enabled": self._state_sync_enabled,
            "interval_s": self._state_sync_interval_s,
            "max_targets": self._state_sync_max_targets,
        }

    def _valid_ips(self, ips) -> set[str]:
        valid: set[str] = set()
        for ip in ips:
            try:
                ipaddress.ip_address(str(ip))
            except ValueError:
                continue
            valid.add(str(ip))
        return valid

    def _reachable_targets(self) -> set[str]:
        targets = set(self.bulbs.keys())
        if self.proto:
            targets |= set(self.proto.discovered.keys())
            targets |= set(self.proto.last_pilot.keys())
        return {
            ip
            for ip in self._valid_ips(targets)
            if not self._is_removed_bulb(ip, self._device_mac(ip))
        }

    def _saved_targets(self) -> set[str]:
        return {
            ip
            for ip in self._valid_ips(self.bulb_ips)
            if not self._is_removed_bulb(ip, self._device_mac(ip))
        }

    def _ensure_active_ip(self) -> str | None:
        reachable = self._reachable_targets()
        saved = self._saved_targets()
        all_known = reachable | saved

        # Si la IP activa no existe, o quedó vieja/offline y hay una viva, cambia a una viva.
        if self._active_ip not in all_known or (reachable and self._active_ip not in reachable):
            preferred = sorted(
                ip for ip in self.bulbs.keys()
                if not self._is_removed_bulb(ip, self._device_mac(ip))
            ) or sorted(reachable) or sorted(saved)
            self._active_ip = preferred[0] if preferred else None
            self._save_control_config()
        return self._active_ip

    def _control_targets(self) -> set[str]:
        reachable = self._reachable_targets()
        if self._target_mode == "single":
            ip = self._ensure_active_ip()
            return {ip} if ip else set()

        # Modo todas: prioriza solo dispositivos vivos/descubiertos; fallback a guardados si nada responde.
        return reachable or self._saved_targets()

    def set_target_mode(self, mode: str) -> None:
        self._target_mode = self._normalise_mode(mode)
        self._ensure_active_ip()
        self._save_control_config()
        self._fire_callback()

    def set_active_bulb(self, ip: str) -> None:
        ip = (ip or "").strip()
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return
        if self._is_removed_bulb(ip, self._device_mac(ip)):
            return
        self._active_ip = ip
        self.bulb_ips.add(ip)
        self._target_mode = "single"
        self._save_control_config()
        self._seed_mirror_from_first_live_bulb(ip)
        self._fire_callback()

    def set_slider_interval_ms(self, ms: int) -> None:
        try:
            ms = int(ms)
        except Exception:
            return
        self._slider_interval_ms = max(35, min(200, ms))
        self.MIN_INTERVAL = self._slider_interval_ms / 1000.0
        self._save_control_config()

    def get_target_config(self) -> dict[str, Any]:
        active = self._ensure_active_ip()
        return {
            "mode": self._target_mode,
            "active_ip": active,
            "targets": sorted(self._control_targets()),
            "reachable": sorted(self._reachable_targets()),
            "saved": sorted(self._saved_targets()),
            "slider_interval_ms": self._slider_interval_ms,
        }

    def cleanup_offline_bulbs(self) -> int:
        """Borra IPs guardadas que no están online ni recién descubiertas."""
        keep = self._reachable_targets()
        removed = 0
        for ip in list(self.bulb_ips):
            if ip not in keep:
                self.bulb_ips.discard(ip)
                self.bulbs.pop(ip, None)
                self.bulbs_manager.remove_bulb(ip)
                removed += 1
        if self._active_ip not in keep:
            self._active_ip = None
            self._ensure_active_ip()
        self._save_control_config()
        self._fire_callback()
        return removed

    # ------------------------------------------------------------------ #
    # Escritura coalescida
    # ------------------------------------------------------------------ #
    async def _pump(self) -> None:
        while self.running:
            if self._dirty and self.proto:
                self._dirty = False
                self._broadcast(dict(self._target))
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
            _LOG.info("[Light] setPilot -> %s params=%s", sorted(targets), params)
            self._last_control_log = now

        now = time.monotonic()
        self._last_control_at = now
        self._sync_boost_until = max(self._sync_boost_until, now + 1.4)
        self._schedule_post_action_verify(targets)

        self._fire_callback(throttle=True)

    def _schedule_post_action_verify(self, targets: set[str]) -> None:
        """Verifica estado real poco después de mandar setPilot.

        Esto mantiene la UI/tray precisos sin esperar ACK en el camino caliente.
        Si la bombilla corrige algún valor o la app móvil interviene, el espejo se ajusta.
        """
        if not self.proto or not targets or not self.loop.is_running():
            return
        for delay in self.POST_ACTION_VERIFY_DELAYS:
            try:
                self.loop.create_task(self._verify_targets_after(sorted(targets), float(delay)))
            except Exception:
                pass

    async def _verify_targets_after(self, targets: list[str], delay: float) -> None:
        await asyncio.sleep(max(0.05, delay))
        if not self.running or not self.proto:
            return
        any_changed = False
        for ip in targets[: max(1, self._state_sync_max_targets)]:
            try:
                pilot = await self.proto.query(
                    ip,
                    "getPilot",
                    self.loop,
                    timeout=self.STATE_SYNC_TIMEOUT,
                    retries=0,
                )
                if pilot:
                    any_changed = self._merge_pilot_state(ip, pilot) or any_changed
            except Exception:
                continue
        if any_changed:
            self._fire_callback()

    def _fire_callback(self, *, throttle: bool = False) -> None:
        if not self._callback:
            return
        now = time.monotonic()
        if throttle and now - self._last_callback_log < self.CALLBACK_MIN_INTERVAL:
            return
        self._last_callback_log = now
        try:
            self._callback(self.get_state())
        except Exception:
            _LOG.debug("[Light] callback falló", exc_info=True)

    # ------------------------------------------------------------------ #
    # Discovery + probing
    # ------------------------------------------------------------------ #
    async def _discover(
        self,
        *,
        aggressive: bool = False,
        scan_claimed: bool = False,
    ) -> bool:
        if not scan_claimed and not self._claim_scan(explicit=False):
            return False

        error: str | None = None
        pywiz_task: asyncio.Task | None = None
        try:
            if not self.proto:
                error = "El transporte UDP todavía no está disponible"
                return False
            if self._scan_lock is None:
                self._scan_lock = asyncio.Lock()

            async with self._scan_lock:
                broadcasts = get_broadcast_addresses()
                local_ip = get_local_ip()
                self.proto.discovered.clear()

                pywiz_task = asyncio.create_task(
                    discover_with_pywizlight(broadcasts, wait_time=1.25)
                )

                for _ in range(self.DISCOVERY_ROUNDS):
                    for bcast in broadcasts:
                        self.proto.send_registration(local_ip, bcast, register=False)
                    await asyncio.sleep(self.DISCOVERY_INTERVAL)

                await asyncio.sleep(0.25)

                try:
                    pywiz_items = await asyncio.wait_for(
                        pywiz_task,
                        timeout=self.PYWIZ_DISCOVERY_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    pywiz_items = []
                    _LOG.warning("[Light] pywizlight excedió el timeout de discovery")

                for item in pywiz_items:
                    ip = item.get("ip")
                    if not ip or self._is_removed_bulb(ip, item.get("mac")):
                        continue
                    prev = self.proto.discovered.get(ip, {})
                    self.proto.discovered[ip] = {
                        **prev,
                        **item,
                        "seen_at": time.time(),
                    }

                # Descarta respuestas UDP tardías de dispositivos quitados.
                for ip, info in list(self.proto.discovered.items()):
                    if self._is_removed_bulb(ip, info.get("mac")):
                        self.proto.discovered.pop(ip, None)
                        self.proto.last_pilot.pop(ip, None)

                candidates = set(self.bulb_ips) | set(self.proto.discovered.keys())
                candidates = {
                    ip
                    for ip in candidates
                    if not self._is_removed_bulb(ip, self._device_mac(ip))
                }

                if aggressive or not candidates:
                    try:
                        candidates |= await asyncio.wait_for(
                            self._scan_subnet(),
                            timeout=self.SUBNET_SCAN_TIMEOUT,
                        )
                    except asyncio.TimeoutError:
                        _LOG.warning("[Light] El escaneo de subred alcanzó su timeout")

                self._remember_discovered_targets()
                candidates |= self._saved_targets()
                candidates = {
                    ip
                    for ip in candidates
                    if not self._is_removed_bulb(ip, self._device_mac(ip))
                }

                await self._probe_many(candidates)
                self._ensure_active_ip()
                self._seed_mirror_from_first_live_bulb()

                _LOG.info(
                    "[Light] Discovery listo. Guardadas=%d, online=%d, modo=%s, activa=%s",
                    len(self._saved_targets()),
                    len(self.bulbs),
                    self._target_mode,
                    self._active_ip,
                )
                return True
        except asyncio.CancelledError:
            error = "Búsqueda cancelada"
            raise
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            _LOG.warning("[Light] discovery falló: %s", error, exc_info=True)
            return False
        finally:
            if pywiz_task is not None and not pywiz_task.done():
                pywiz_task.cancel()
            self._finish_scan(error)

    async def _scan_subnet(self) -> set[str]:
        if not self.proto:
            return set()

        ips = [
            ip
            for ip in get_lan_scan_ips(limit=512)
            if ip not in self.bulb_ips and not self._is_removed_bulb(ip)
        ]
        found: set[str] = set()
        sem = asyncio.Semaphore(self.SCAN_CONCURRENCY)

        async def check(ip: str) -> None:
            async with sem:
                res = await self.proto.query(
                    ip,
                    "getSystemConfig",
                    self.loop,
                    timeout=self.SCAN_TIMEOUT,
                    retries=0,
                )
                if (
                    res
                    and not self._is_removed_bulb(ip, res.get("mac"))
                    and (res.get("mac") or res.get("moduleName") or res.get("fwVersion"))
                ):
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
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                continue

            mac = info.get("mac")
            module = info.get("moduleName") or info.get("module")
            if self._is_removed_bulb(ip, mac):
                self.proto.discovered.pop(ip, None)
                self.proto.last_pilot.pop(ip, None)
                continue
            self.bulb_ips.add(ip)

            payload: dict[str, Any] = {"ip": ip, "mac": mac, "port": WIZ_PORT}
            if module:
                payload["module"] = module
            if isinstance(saved, dict) and ip in saved and saved[ip].get("name"):
                payload["name"] = saved[ip]["name"]
            self.bulbs_manager.add_bulb(payload)

    async def _probe_many(self, ips: set[str]) -> None:
        sem = asyncio.Semaphore(self.PROBE_CONCURRENCY)
        allowed = {
            ip
            for ip in ips
            if not self._is_removed_bulb(ip, self._device_mac(ip))
        }

        async def one(ip: str) -> None:
            async with sem:
                await self._probe(ip)

        await asyncio.gather(*(one(ip) for ip in sorted(allowed)), return_exceptions=True)

    async def _probe(self, ip: str) -> bool:
        if not self.proto or self._is_removed_bulb(ip, self._device_mac(ip)):
            self._purge_device_cache(ip)
            return False

        sys_task = asyncio.create_task(
            self.proto.query(ip, "getSystemConfig", self.loop, self.QUERY_TIMEOUT)
        )
        pilot_task = asyncio.create_task(
            self.proto.query(ip, "getPilot", self.loop, self.QUERY_TIMEOUT)
        )
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
        mac = (
            (sysc or {}).get("mac")
            or (pilot or {}).get("mac")
            or discovered.get("mac")
            or saved_entry.get("mac")
        )
        if self._is_removed_bulb(ip, mac):
            self._purge_device_cache(ip)
            return False
        caps = from_wiz_config(sysc, model, pilot)
        name = saved_entry.get("name")

        real_state = pilot or self.proto.last_pilot.get(ip, {})
        self.bulbs[ip] = {
            "ip": ip,
            "mac": mac,
            "caps": caps,
            "state": real_state,
            "name": name,
            "module": module,
            "system": sysc or {},
            "model": model or {},
            "rssi": (real_state or {}).get("rssi"),
            "last_seen": time.time(),
        }
        if real_state:
            self._last_state_signature[ip] = self._state_signature(real_state)
        self.bulb_ips.add(ip)

        payload: dict[str, Any] = {"ip": ip, "mac": mac, "port": WIZ_PORT, "module": module}
        if name:
            payload["name"] = name
        self.bulbs_manager.add_bulb(payload)
        return True

    def _seed_mirror_from_first_live_bulb(self, preferred_ip: str | None = None) -> None:
        order: list[str] = []
        if preferred_ip:
            order.append(preferred_ip)
        if self._active_ip and self._active_ip not in order:
            order.append(self._active_ip)
        order.extend([ip for ip in self.bulbs.keys() if ip not in order])

        for ip in order:
            info = self.bulbs.get(ip)
            if not info or self._is_removed_bulb(ip, info.get("mac")):
                continue
            st = info.get("state") or {}
            for key in ("state", "dimming", "temp", "sceneId", "speed", "r", "g", "b", "c", "w", "ratio"):
                if key in st:
                    self._mirror[key] = st[key]
            break

    async def _refresh_async(self) -> None:
        await self._probe_many(self._saved_targets())
        self._ensure_active_ip()
        self._seed_mirror_from_first_live_bulb()
        self._fire_callback()

    def refresh(self) -> None:
        self._run_coro(self._refresh_async())

    # ------------------------------------------------------------------ #
    # Sync de estado real: cambios hechos desde celular/app WiZ
    # ------------------------------------------------------------------ #
    def _state_signature(self, state: dict[str, Any] | None) -> tuple:
        st = state or {}
        keys = ("state", "dimming", "temp", "sceneId", "speed", "r", "g", "b", "c", "w", "ratio")
        return tuple((k, st.get(k)) for k in keys if k in st)

    def _state_sync_ips(self) -> list[str]:
        # En modo single, el polling debe ser casi gratis: solo la ampolleta activa.
        active = self._ensure_active_ip()
        ordered: list[str] = []
        if active:
            ordered.append(active)
        live = {
            ip
            for ip in self.bulbs.keys()
            if not self._is_removed_bulb(ip, self._device_mac(ip))
        }
        for ip in sorted(self._control_targets() | live):
            if ip and ip not in ordered:
                ordered.append(ip)
        return ordered[: self._state_sync_max_targets]

    def _merge_pilot_state(self, ip: str, pilot: dict[str, Any]) -> bool:
        if not pilot:
            return False
        if self._is_removed_bulb(ip, pilot.get("mac") or self._device_mac(ip)):
            self._purge_device_cache(ip)
            return False

        before = self._last_state_signature.get(ip)
        after = self._state_signature(pilot)
        mirror_before = self._state_signature(self._mirror)

        # Importante: before puede ser None si el primer probe no alcanzó a leer getPilot.
        # En ese caso igual hay que actualizar la UI si el piloto trae estado real.
        changed = before != after
        self._last_state_signature[ip] = after
        self._last_successful_sync_at = time.time()

        if ip in self.bulbs:
            self.bulbs[ip]["state"] = pilot
            self.bulbs[ip]["rssi"] = pilot.get("rssi", self.bulbs[ip].get("rssi"))
            self.bulbs[ip]["last_seen"] = time.time()
        elif self.proto and ip in self.proto.discovered:
            self.bulb_ips.add(ip)

        active = self._ensure_active_ip()
        if ip == active or (self._target_mode == "all" and active is None):
            for key in ("state", "dimming", "temp", "sceneId", "speed", "r", "g", "b", "c", "w", "ratio"):
                if key in pilot:
                    self._mirror[key] = pilot[key]

            # Limpiar modos mutuamente excluyentes para que la UI no quede mezclada.
            if "sceneId" in pilot:
                for k in ("r", "g", "b", "c", "w", "temp"):
                    if k not in pilot:
                        self._mirror.pop(k, None)
            elif "temp" in pilot:
                for k in ("r", "g", "b", "c", "w", "sceneId", "speed"):
                    if k not in pilot:
                        self._mirror.pop(k, None)
            elif all(k in pilot for k in ("r", "g", "b")):
                for k in ("temp", "sceneId", "speed"):
                    if k not in pilot:
                        self._mirror.pop(k, None)

            changed = changed or self._state_signature(self._mirror) != mirror_before
        return changed

    def _state_sync_sleep_interval(self, changed: bool = False) -> float:
        # Punto dulce: rápido con una ampolleta, prudente en segundo plano/múltiples targets.
        now = time.monotonic()
        if changed:
            self._sync_boost_until = max(self._sync_boost_until, now + 1.2)
            return 0.16
        if now < self._sync_boost_until:
            return 0.22
        if self._target_mode == "single":
            return min(self._state_sync_interval_s, 0.35)
        return max(self._state_sync_interval_s, 0.85)

    async def _state_sync_loop(self) -> None:
        # Da tiempo al discovery inicial; después queda como monitor liviano.
        await asyncio.sleep(0.8)
        while self.running:
            any_changed = False
            try:
                if self._state_sync_enabled and self.proto:
                    for ip in self._state_sync_ips():
                        pilot = await self.proto.query(
                            ip,
                            "getPilot",
                            self.loop,
                            timeout=self.STATE_SYNC_TIMEOUT,
                            retries=0,
                        )
                        if pilot:
                            any_changed = self._merge_pilot_state(ip, pilot) or any_changed

                    if any_changed:
                        now = time.monotonic()
                        if now - self._last_state_sync_log > 0.6:
                            _LOG.info("[Light] Estado externo sincronizado desde WiZ/app móvil")
                            self._last_state_sync_log = now
                        self._fire_callback()
            except Exception:
                _LOG.debug("[Light] state sync falló", exc_info=True)
            await asyncio.sleep(self._state_sync_sleep_interval(any_changed))

    # ------------------------------------------------------------------ #
    # Gestión de ampolletas para Ajustes
    # ------------------------------------------------------------------ #
    def rescan(self) -> bool:
        """Inicia una búsqueda explícita sin encolar scans duplicados."""
        if not self._claim_scan(explicit=True):
            return False
        future = self._run_coro(
            self._discover(aggressive=True, scan_claimed=True)
        )
        if future is None:
            self._finish_scan("El servicio de red todavía no está listo")
            return False
        return True

    def add_bulb_manual(self, ip: str) -> bool:
        ip = (ip or "").strip()
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            _LOG.warning("IP inválida: %s", ip)
            return False

        self._forget_removed_bulb(ip=ip)
        self.bulb_ips.add(ip)
        self.bulbs_manager.add_bulb({"ip": ip, "mac": None, "port": WIZ_PORT})
        if not self._active_ip:
            self._active_ip = ip
            self._save_control_config()
        fut = self._run_coro(self._probe_then_notify(ip))
        if fut is None:
            self._fire_callback()
        return True

    async def _probe_then_notify(self, ip: str) -> None:
        await self._probe(ip)
        self._ensure_active_ip()
        self._fire_callback()

    def rename_bulb(self, ip: str, name: str) -> None:
        self.bulbs_manager.set_bulb_name(ip, name)
        if ip in self.bulbs:
            self.bulbs[ip]["name"] = name
        self._fire_callback()

    def remove_bulb(self, ip: str) -> bool:
        """Quita una ampolleta y evita que caches/discovery la revivan.

        La lápida se mantiene entre reinicios. Una búsqueda explícita la limpia,
        porque «Buscar ampolletas» significa volver a admitir dispositivos LAN.
        """
        ip = str(ip or "").strip()
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return False

        saved = self.bulbs_manager.get_bulbs()
        saved_entry = saved.get(ip, {}) if isinstance(saved, dict) else {}
        live_entry = self.bulbs.get(ip, {})
        discovered = self.proto.discovered.get(ip, {}) if self.proto else {}
        mac = (
            live_entry.get("mac")
            or discovered.get("mac")
            or (saved_entry.get("mac") if isinstance(saved_entry, dict) else None)
        )
        existed = bool(
            ip in self.bulb_ips
            or ip in self.bulbs
            or (self.proto and (ip in self.proto.discovered or ip in self.proto.last_pilot))
            or (isinstance(saved, dict) and ip in saved)
        )

        self._remember_removed_bulb(ip, mac)
        self._purge_device_cache(ip)
        self.bulbs_manager.remove_bulb(ip)

        if self._active_ip == ip:
            self._active_ip = None
            self._ensure_active_ip()
            self._save_control_config()
        self._fire_callback()
        return existed

    def get_bulbs_detailed(self) -> list[dict[str, Any]]:
        self._prune_removed_protocol_cache()
        saved = self.bulbs_manager.get_bulbs()
        out: list[dict[str, Any]] = []
        target_cfg = self.get_target_config()
        reachable = self._reachable_targets()
        candidates = self._saved_targets() | reachable

        for ip in sorted(candidates):
            info = self.bulbs.get(ip, {})
            saved_entry = saved.get(ip, {}) if isinstance(saved, dict) else {}
            mac = info.get("mac") or saved_entry.get("mac")
            if self._is_removed_bulb(ip, mac):
                continue
            caps: Capabilities | None = info.get("caps")
            state = info.get("state") or {}
            out.append(
                {
                    "ip": ip,
                    "name": info.get("name") or saved_entry.get("name") or ip,
                    "mac": mac,
                    "label": caps.label if caps else "—",
                    "online": ip in self.bulbs or ip in reachable,
                    "active": ip == target_cfg.get("active_ip"),
                    "targeted": ip in set(target_cfg.get("targets", [])),
                    "module": info.get("module") or saved_entry.get("module"),
                    "rssi": state.get("rssi") or info.get("rssi"),
                    "dimming": state.get("dimming"),
                    "state": state.get("state"),
                    "temp": state.get("temp"),
                    "sceneId": state.get("sceneId"),
                    "last_seen": info.get("last_seen"),
                    "kelvin_min": caps.kelvin_min if caps else None,
                    "kelvin_max": caps.kelvin_max if caps else None,
                    "rgb": bool(caps.rgb) if caps else None,
                    "tunable_white": bool(caps.tunable_white) if caps else None,
                }
            )
        return out

    def get_device_info(self, ip: str | None = None) -> dict[str, Any]:
        ip = ip or self._ensure_active_ip()
        if not ip:
            return {}
        items = {b["ip"]: b for b in self.get_bulbs_detailed()}
        info = dict(items.get(ip, {}))
        raw = self.bulbs.get(ip, {})
        caps: Capabilities | None = raw.get("caps")
        if caps:
            info["capabilities"] = caps.__dict__.copy()
        info["system"] = raw.get("system", {})
        info["model_config"] = raw.get("model", {})
        info["raw_state"] = raw.get("state", {})
        return info

    def get_tray_status(self) -> dict[str, Any]:
        """Estado compacto para bandeja/panel rápido."""
        info = self.get_device_info() or {}
        state = self.get_state()
        summary = self.summary()
        last_seen = info.get("last_seen") or self._last_successful_sync_at or None
        age = None
        if last_seen:
            try:
                age = max(0.0, time.time() - float(last_seen))
            except Exception:
                age = None
        return {
            "name": info.get("name") or summary.get("active_ip") or "Ampolleta",
            "ip": summary.get("active_ip"),
            "online": bool(summary.get("active", 0) > 0),
            "mode": summary.get("target_mode", "single"),
            "state": state,
            "summary": summary,
            "last_sync_age": age,
            "label": info.get("label") or summary.get("label") or "",
            "rssi": info.get("rssi"),
        }

    # ------------------------------------------------------------------ #
    # API pública de control
    # ------------------------------------------------------------------ #

    def apply_favorite(self, fav: dict[str, Any]) -> None:
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "rgb":
            h = str(value).strip().lstrip("#")
            if len(h) == 6:
                self.set_rgb(*(int(h[i:i + 2], 16) for i in (0, 2, 4)))
        elif ftype == "white":
            self.set_white(int(value))
        elif ftype == "brightness":
            self.set_brightness(int(value))
        elif ftype == "scene":
            if isinstance(value, dict):
                self.set_scene(int(value.get("sceneId", 1)), value.get("speed"))
            else:
                self.set_scene(int(value))

    def _drop_mode_keys(self, *keys: str) -> None:
        for key in keys:
            self._target.pop(key, None)
            self._mirror.pop(key, None)

    def _mark(self) -> None:
        self._mirror.update(self._target)
        self._dirty = True

    def set_rgb(self, r: int, g: int, b: int) -> None:
        """Set a logical display sRGB colour using WiZ RGBTW emitters.

        Pastel/near-white colours cannot be reproduced faithfully by driving
        only the RGB LEDs of an RGBTW bulb.  The WiZ-aware conversion adds the
        warm-white contribution while the public state preserves the exact sRGB
        requested by the UI, routines, favourites and tray.
        """

        logical = normalize_rgb((r, g, b))
        device = display_rgb_to_wiz_channels(logical)
        self._logical_rgb = logical
        self._logical_rgb_device = wiz_channels_signature(device)
        self._target.update({"state": True, **device})
        self._drop_mode_keys("temp", "sceneId", "speed", "c", "cw", "ww", "temperature")
        self._mark()

    def set_white(self, kelvin: int) -> None:
        lo, hi = self.get_kelvin_range()
        kelvin = max(lo, min(hi, int(kelvin)))
        self._target.update({"state": True, "temp": kelvin})
        self._drop_mode_keys("r", "g", "b", "sceneId", "speed", "c", "w", "cw", "ww")
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
        self._target["dimming"] = int(max(10, min(100, pct)))
        self._mark()

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
        self._target.clear()
        self._mirror.clear()
        self._mirror.update({"state": True, "dimming": 100, "temp": neutral})
        self._target.update({"state": True, "dimming": 100, "temp": neutral})
        self._dirty = True

    def get_state(self) -> dict[str, Any]:
        """Return logical UI state while retaining raw WiZ RGBTW diagnostics."""

        state = dict(self._mirror)
        if all(key in state for key in ("r", "g", "b")):
            raw_signature = wiz_channels_signature(state)
            logical = logical_rgb_from_state(
                state,
                last_logical_rgb=getattr(self, "_logical_rgb", None),
                last_device_signature=getattr(self, "_logical_rgb_device", None),
            )
            if logical is not None:
                state["device_color"] = {
                    "r": raw_signature[0],
                    "g": raw_signature[1],
                    "b": raw_signature[2],
                    "c": raw_signature[3],
                    "w": raw_signature[4],
                }
                state["r"], state["g"], state["b"] = logical
        return state

    def apply_custom_scene(self, scene: dict[str, Any]) -> None:
        """Aplica una escena personalizada local de la app.

        Formatos soportados:
        - {mode: rgb, value:{r,g,b,dimming?}}
        - {mode: white, value:{temp,dimming?}}
        - {mode: scene, value:{sceneId,speed?,dimming?}}
        - {mode: combo, value:[{type:..., value:...}, ...]}
        """
        if not scene:
            return
        mode = str(scene.get("mode") or scene.get("type") or "").lower()
        value = scene.get("value") or {}

        def maybe_dim(v):
            if isinstance(v, dict) and "dimming" in v:
                self.set_brightness(int(v.get("dimming", 100)))

        if mode == "rgb":
            if isinstance(value, str):
                h = value.strip().lstrip("#")
                if len(h) == 6:
                    self.set_rgb(*(int(h[i:i + 2], 16) for i in (0, 2, 4)))
                    return
            if isinstance(value, dict):
                self.set_rgb(int(value.get("r", 255)), int(value.get("g", 0)), int(value.get("b", 0)))
                maybe_dim(value)
        elif mode == "white":
            if isinstance(value, dict):
                self.set_white(int(value.get("temp", value.get("kelvin", 4000))))
                maybe_dim(value)
            else:
                self.set_white(int(value))
        elif mode == "scene":
            if isinstance(value, dict):
                self.set_scene(int(value.get("sceneId", 18)), value.get("speed"))
                maybe_dim(value)
            else:
                self.set_scene(int(value))
        elif mode == "brightness":
            self.set_brightness(int(value.get("dimming", value) if isinstance(value, dict) else value))
        elif mode == "combo" and isinstance(value, list):
            for step in value[:8]:
                self.apply_custom_scene(step)

    def capture_current_scene_payload(self) -> dict[str, Any]:
        """Devuelve un payload estable para guardar la luz actual como escena."""
        st = self.get_state()
        dimming = int(st.get("dimming", 100) or 100)
        if "sceneId" in st:
            return {"mode": "scene", "value": {"sceneId": int(st.get("sceneId", 18)), "speed": int(st.get("speed", 100) or 100), "dimming": dimming}}
        if "temp" in st:
            return {"mode": "white", "value": {"temp": int(st.get("temp", 4000)), "dimming": dimming}}
        if all(k in st for k in ("r", "g", "b")):
            return {"mode": "rgb", "value": {"r": int(st.get("r", 255)), "g": int(st.get("g", 255)), "b": int(st.get("b", 255)), "dimming": dimming}}
        return {"mode": "white", "value": {"temp": 4000, "dimming": dimming}}

    # ------------------------------------------------------------------ #
    # Compatibilidad UI fase 3
    # ------------------------------------------------------------------ #
    def get_control_config(self) -> dict[str, Any]:
        return self.get_target_config()

    def set_control_mode(self, mode: str) -> None:
        self.set_target_mode(mode)

    def set_selected_bulb(self, ip: str) -> None:
        self.set_active_bulb(ip)

    def prune_offline_bulbs(self) -> int:
        return self.cleanup_offline_bulbs()

    def get_selected_bulb_info(self) -> dict[str, Any] | None:
        info = self.get_device_info()
        return info or None

    def kelvin_from_percent(self, pct: int | float) -> int:
        lo, hi = self.get_kelvin_range()
        p = max(0.0, min(100.0, float(pct))) / 100.0
        return int(round(lo + (hi - lo) * p))

    def percent_from_kelvin(self, kelvin: int | float) -> int:
        lo, hi = self.get_kelvin_range()
        if hi <= lo:
            return 50
        return int(round((float(kelvin) - lo) * 100 / (hi - lo)))

    def adjust_brightness(self, delta: int) -> None:
        cur = int(self._mirror.get("dimming", 100) or 100)
        self.set_brightness(cur + int(delta))

    def reset_brightness(self) -> None:
        self.set_brightness(100)

    def adjust_temperature_percent(self, delta: int) -> None:
        cur = self.percent_from_kelvin(int(self._mirror.get("temp", self.kelvin_from_percent(50))))
        self.set_white_percent(cur + int(delta))

    def reset_temperature(self) -> None:
        self.set_white_percent(50)

    # ------------------------------------------------------------------ #
    # Capacidades agregadas para UI
    # ------------------------------------------------------------------ #
    def get_kelvin_range(self) -> tuple[int, int]:
        ip = self._ensure_active_ip()
        if ip and ip in self.bulbs:
            caps = self.bulbs[ip].get("caps")
            if caps:
                return int(caps.kelvin_min), int(caps.kelvin_max)

        caps_list = [b.get("caps") for b in self.bulbs.values() if b.get("caps")]
        if caps_list:
            return min(c.kelvin_min for c in caps_list), max(c.kelvin_max for c in caps_list)
        return 2200, 6500

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

        discovered = len(self._reachable_targets()) if self.proto else 0
        target_cfg = self.get_target_config()
        return {
            "count": len(self._saved_targets()),
            "active": len(self.bulbs),
            "discovered": discovered,
            "targets": len(target_cfg.get("targets", [])),
            "target_mode": self._target_mode,
            "active_ip": target_cfg.get("active_ip"),
            "state_sync": self.get_state_sync_config(),
            "label": label,
        }

    def supports_color(self) -> bool:
        ip = self._ensure_active_ip()
        if ip and ip in self.bulbs and self.bulbs[ip].get("caps"):
            return bool(self.bulbs[ip]["caps"].rgb)
        return any(b["caps"].rgb for b in self.bulbs.values() if b.get("caps")) or not self.bulbs
