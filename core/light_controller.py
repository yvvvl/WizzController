import asyncio
import logging
import threading
import sys
import time
from typing import List, Callable, Optional, Dict, Any

from pywizlight import wizlight, PilotBuilder, discovery
from pywizlight.bulb import PilotParser
from config.bulbs_manager import BulbsManager

try:
    from core.event_bus import EventBus
except ImportError:
    EventBus = None

class LightController:
    def __init__(self, event_bus=None):
        self.logger = logging.getLogger(__name__)
        self.bulbs_manager = BulbsManager()
        self.bulbs: List[wizlight] = []
        self.callback: Optional[Callable] = None
        self.event_bus = event_bus
        
        self.running = True
        self.last_command_time = 0
        self.monitor_cooldown = 2.0

        self.state_poll_interval = 2.5
        self._last_state_poll = 0.0
        self._bulb_states: Dict[str, Dict[str, Any]] = {}
        self._bulb_states_lock = threading.Lock()

        # Backoff por IP cuando una bombilla no responde (evita spamear red/CPU)
        self._poll_backoff: Dict[str, Dict[str, Any]] = {}

        # Configurable (eco)
        self._poll_backoff_base_s: float = 2.0
        self._poll_backoff_max_s: float = 30.0
        self._command_active_sleep_s: float = 0.10
        self._command_idle_sleep_s: float = 0.35
        self._monitor_no_bulbs_sleep_s: float = 3.0

        # Polling adaptativo (hyper liviano en idle, rÃ¡pido en actividad)
        self._adaptive_polling_enabled: bool = True
        self._state_poll_min_interval_s: float = 2.5
        self._state_poll_max_interval_s: float = 10.0
        self._state_poll_idle_after_s: float = 12.0
        self._state_poll_growth_factor: float = 1.4
        self._active_until: float = 0.0
        self._last_change_ts: float = time.time()

        # Discovery throttling
        self._discovery_next_ts: float = 0.0
        self._discovery_fails: int = 0
        self._discovery_min_interval_s: float = 60.0
        self._discovery_backoff_max_s: float = 600.0

        # --- OptimizaciÃ³n: coalescing de comandos + pausa de polling durante interacciÃ³n ---
        # En lugar de encolar N comandos (que genera latencia), guardamos solo el Ãºltimo.
        self._pending_pilots_by_ip: Dict[str, Any] = {}
        self._pending_pilot_global: Any | None = None
        self._pending_pilots_lock = threading.Lock()

        # Si el usuario estÃ¡ arrastrando sliders, no competir con polling de estado.
        self._interaction_until: float = 0.0

        # Cuando la app estÃ¡ en segundo plano, podemos pausar el polling para ahorrar recursos.
        self._polling_paused: bool = False
        
        self._current_state = {
            "state": False,
            "brightness": 100,
            "temp": 2700,
            "rgb": (0, 0, 0),
            "cw": 0,
            "ww": 0,
            "sceneId": 0,
            "speed": 100,
            "ratio": 0,
        }
        
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = asyncio.new_event_loop()

        self._loop_ready = threading.Event()

        self.thread = threading.Thread(target=self._start_background_loop, daemon=True)
        self.thread.start()

        # Evita carrera: asegura que el event loop estÃ© inicializado antes de usarlo.
        try:
            self._loop_ready.wait(timeout=1.0)
        except Exception:
            pass

    def stop(self, timeout: float = 2.0) -> None:
        """Detiene el loop de asyncio y el hilo de background."""
        self.running = False
        try:
            if self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            self.logger.exception("Error deteniendo event loop")

        try:
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=timeout)
        except Exception:
            self.logger.exception("Error esperando thread de LightController")

    def start(self):
        self.logger.info("[LightController] Iniciando servicios...")
        known = self.bulbs_manager.get_bulbs()
        for ip in known: self._add_bulb_by_ip(ip)
        self.discover()

    def apply_performance_config(self, perf: Dict[str, Any] | None) -> None:
        """Aplica configuraciÃ³n de performance/eco desde config.json."""
        if not isinstance(perf, dict):
            return

        # Perfiles de performance (los valores explÃ­citos en perf siempre ganan)
        try:
            profile = str(perf.get("profile", "balanced")).lower().strip()
        except Exception:
            profile = "balanced"

        profile_defaults: Dict[str, Any] = {}
        if profile in ("ultra", "ultra_light", "ultralight"):
            profile_defaults = {
                # MÃ¡s liviano, pero puede tardar mÃ¡s en reflejar cambios externos
                "state_poll_max_interval_s": 12.0,
                "state_poll_idle_after_s": 8.0,
                "command_idle_sleep_s": 0.80,
                "monitor_no_bulbs_sleep_s": 6.0,
                "discovery_min_interval_s": 300.0,
                "discovery_backoff_max_s": 1800.0,
            }
        else:
            # balanced (por defecto)
            profile_defaults = {
                "state_poll_max_interval_s": 8.0,
                "state_poll_idle_after_s": 8.0,
                "command_idle_sleep_s": 0.35,
                "monitor_no_bulbs_sleep_s": 3.0,
                "discovery_min_interval_s": 60.0,
                "discovery_backoff_max_s": 600.0,
            }

        # Mezcla: defaults de perfil <- perf
        merged = dict(profile_defaults)
        merged.update(perf)

        def _f(key: str, default: float) -> float:
            try:
                return float(merged.get(key, default))
            except Exception:
                return default

        def _b(key: str, default: bool) -> bool:
            try:
                return bool(merged.get(key, default))
            except Exception:
                return default

        # Compat: tratar state_poll_interval_s como mÃ­nimo
        compat_min = _f("state_poll_interval_s", self._state_poll_min_interval_s)

        self._adaptive_polling_enabled = _b("adaptive_polling_enabled", self._adaptive_polling_enabled)
        self._state_poll_min_interval_s = _f("state_poll_min_interval_s", compat_min)
        self._state_poll_max_interval_s = _f("state_poll_max_interval_s", self._state_poll_max_interval_s)
        self._state_poll_idle_after_s = _f("state_poll_idle_after_s", self._state_poll_idle_after_s)
        self._state_poll_growth_factor = _f("state_poll_growth_factor", self._state_poll_growth_factor)

        # Seguridad
        if self._state_poll_max_interval_s < self._state_poll_min_interval_s:
            self._state_poll_max_interval_s = self._state_poll_min_interval_s
        self._state_poll_growth_factor = max(1.05, min(2.0, float(self._state_poll_growth_factor)))

        # Intervalo actual (arrancar rÃ¡pido)
        self.state_poll_interval = float(self._state_poll_min_interval_s)

        self._poll_backoff_base_s = _f("poll_backoff_base_s", self._poll_backoff_base_s)
        self._poll_backoff_max_s = _f("poll_backoff_max_s", self._poll_backoff_max_s)
        self._command_active_sleep_s = _f("command_active_sleep_s", self._command_active_sleep_s)
        self._command_idle_sleep_s = _f("command_idle_sleep_s", self._command_idle_sleep_s)
        self._monitor_no_bulbs_sleep_s = _f("monitor_no_bulbs_sleep_s", self._monitor_no_bulbs_sleep_s)
        self._discovery_min_interval_s = _f("discovery_min_interval_s", self._discovery_min_interval_s)
        self._discovery_backoff_max_s = _f("discovery_backoff_max_s", self._discovery_backoff_max_s)

    def set_user_interacting(self, seconds: float = 0.7) -> None:
        """SeÃ±al desde UI: el usuario estÃ¡ interactuando (drag).

        Pausa temporalmente el polling para que los comandos tengan prioridad.
        """
        try:
            self._interaction_until = max(self._interaction_until, time.time() + float(seconds))
        except Exception:
            self._interaction_until = time.time() + 0.7

        # Actividad: mantener polling rÃ¡pido un rato
        try:
            self._active_until = max(self._active_until, time.time() + 2.0)
            if self._adaptive_polling_enabled:
                self.state_poll_interval = float(self._state_poll_min_interval_s)
        except Exception:
            pass

    def set_polling_paused(self, paused: bool) -> None:
        """Pausa/reanuda el polling de estado (para modo segundo plano)."""
        self._polling_paused = bool(paused)

        if not self._polling_paused:
            # Al volver a foreground, refrescar rÃ¡pido
            try:
                self._active_until = max(self._active_until, time.time() + 2.0)
                if self._adaptive_polling_enabled:
                    self.state_poll_interval = float(self._state_poll_min_interval_s)
            except Exception:
                pass

    def discover(self) -> None:
        """Lanza discovery en el loop de background (no bloquea UI)."""
        now = time.time()
        if now < self._discovery_next_ts:
            return

        # throttle: no lances discover demasiado seguido.
        self._discovery_next_ts = now + float(self._discovery_min_interval_s)

        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._discover_bulbs(), self.loop)

    def set_callback(self, callback: Callable):
        self.callback = callback

    def turn_on(self, ip: str | None = None):
        self._update_local(state=True)
        # Al encender sin params, restauramos el Ãºltimo estado
        self._enqueue_pilot(PilotBuilder(state=True), ip=ip)

    def turn_off(self, ip: str | None = None):
        """MÃ©todo de apagado reforzado"""
        self._update_local(state=False)
        self.last_command_time = time.time()
        
        if not self.bulbs: return

        async def _off():
            targets = self._get_bulbs(ip)
            for bulb in targets:
                try: 
                    # Usamos el mÃ©todo nativo turn_off de la librerÃ­a para mayor seguridad
                    await bulb.turn_off()
                except Exception as e: 
                    logging.error(f"Error apagando {bulb.ip}: {e}")
        
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_off(), self.loop)

    def toggle(self):
        if self._current_state["state"]: self.turn_off()
        else: self.turn_on()

    def set_rgb(self, r, g, b, ip: str | None = None, emit: bool = True):
        if emit:
            self._update_local(state=True, rgb=(r, g, b))
        self._enqueue_pilot(PilotBuilder(rgb=(r, g, b)), ip=ip)

    def set_white(self, kelvin, ip: str | None = None, emit: bool = True):
        k = max(2200, min(6500, kelvin))
        if emit:
            self._update_local(state=True, temp=k)
        self._enqueue_pilot(PilotBuilder(colortemp=k), ip=ip)

    def set_brightness(self, intensity, ip: str | None = None, emit: bool = True):
        val = max(10, min(100, intensity))
        if emit:
            self._update_local(brightness=val)
        wiz_val = int((val / 100) * 255)
        self._enqueue_pilot(PilotBuilder(brightness=wiz_val), ip=ip)

    def set_scene(self, scene_id, ip: str | None = None):
        self._update_local(state=True, sceneId=scene_id)
        self._enqueue_pilot(PilotBuilder(scene=scene_id), ip=ip)

    def apply_piloting_state(self, state: Dict[str, Any], ip: str | None = None, emit: bool = True) -> None:
        """Aplica un estado estilo WiZ Pro (PilotingLightStateInput) usando pywizlight.

        Campos soportados (todos opcionales):
        - r,g,b (0-255)
        - cw,ww (0-255)  -> cold_white / warm_white
        - dimming (10-100) -> brightness (0-255)
        - temperature (K) -> colortemp
        - sceneId (int) -> scene
        - speed (20-200)
        - ratio (0-100)
        - state (bool)
        """

        if not isinstance(state, dict):
            return

        def _clamp_int(v: Any, lo: int, hi: int) -> int:
            try:
                iv = int(v)
            except Exception:
                iv = lo
            if iv < lo:
                return lo
            if iv > hi:
                return hi
            return iv

        pb_kwargs: Dict[str, Any] = {}
        local_updates: Dict[str, Any] = {}

        # Determina si el comando implica "encender"
        implies_on = False

        if "state" in state and state["state"] is not None:
            pb_kwargs["state"] = bool(state["state"])
            local_updates["state"] = bool(state["state"])

        # Dimming (10-100)
        if "dimming" in state and state["dimming"] is not None:
            dim = _clamp_int(state["dimming"], 10, 100)
            local_updates["brightness"] = dim
            pb_kwargs["brightness"] = int((dim / 100) * 255)
            implies_on = True

        # Temperature (K)
        if "temperature" in state and state["temperature"] is not None:
            k = _clamp_int(state["temperature"], 2200, 6500)
            local_updates["temp"] = k
            pb_kwargs["colortemp"] = k
            implies_on = True

        # RGB
        if any(k in state for k in ("r", "g", "b")):
            r = _clamp_int(state.get("r", 0), 0, 255)
            g = _clamp_int(state.get("g", 0), 0, 255)
            b = _clamp_int(state.get("b", 0), 0, 255)
            local_updates["rgb"] = (r, g, b)
            pb_kwargs["rgb"] = (r, g, b)
            implies_on = True

        # CW/WW tracks
        if "cw" in state and state["cw"] is not None:
            cw = _clamp_int(state["cw"], 0, 255)
            local_updates["cw"] = cw
            pb_kwargs["cold_white"] = cw
            implies_on = True

        if "ww" in state and state["ww"] is not None:
            ww = _clamp_int(state["ww"], 0, 255)
            local_updates["ww"] = ww
            pb_kwargs["warm_white"] = ww
            implies_on = True

        # Scene
        if "sceneId" in state and state["sceneId"] is not None:
            sid = _clamp_int(state["sceneId"], 0, 1000)
            local_updates["sceneId"] = sid
            pb_kwargs["scene"] = sid
            implies_on = True

        # Speed
        if "speed" in state and state["speed"] is not None:
            sp = _clamp_int(state["speed"], 20, 200)
            local_updates["speed"] = sp
            pb_kwargs["speed"] = sp

        # Ratio
        if "ratio" in state and state["ratio"] is not None:
            ra = _clamp_int(state["ratio"], 0, 100)
            local_updates["ratio"] = ra
            pb_kwargs["ratio"] = ra

        # Si no nos dieron state explÃ­cito, pero estamos cambiando algo, encendemos.
        if implies_on and "state" not in pb_kwargs:
            pb_kwargs["state"] = True
            local_updates["state"] = True

        if not pb_kwargs:
            return

        if emit and local_updates:
            self._update_local(**local_updates)

        self._enqueue_pilot(PilotBuilder(**pb_kwargs), ip=ip)

    def get_state(self):
        return self._current_state

    def get_bulb_state(self, ip: str) -> Dict[str, Any] | None:
        with self._bulb_states_lock:
            st = self._bulb_states.get(ip)
            return dict(st) if isinstance(st, dict) else None

    def get_bulb_states_snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._bulb_states_lock:
            return {ip: dict(st) for ip, st in self._bulb_states.items()}

    def _update_local(self, **kwargs):
        # Evitar notificar si no hay cambios reales (reduce trabajo de UI)
        changed = False
        for k, v in kwargs.items():
            if self._current_state.get(k) != v:
                changed = True
                break
        if not changed:
            return

        self._current_state.update(kwargs)
        if self.callback: 
            try:
                self.callback(self._current_state)
            except Exception:
                self.logger.exception("Error en callback de UI")
        if self.event_bus:
            self.event_bus.emit("light_state_changed", self._current_state)

    def _get_bulbs(self, ip: str | None = None) -> List[wizlight]:
        if not ip:
            return list(self.bulbs)
        return [b for b in self.bulbs if getattr(b, "ip", None) == ip]

    def _send_command(self, pilot, ip: str | None = None):
        self.last_command_time = time.time()
        if not self.bulbs: return
        async def _send():
            for bulb in self._get_bulbs(ip):
                try:
                    await bulb.turn_on(pilot)
                except Exception as e:
                    self.logger.error(f"Error enviando comando a {getattr(bulb, 'ip', '?')}: {e}")
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), self.loop)

    def _enqueue_pilot(self, pilot, ip: str | None = None) -> None:
        """Guarda el Ãºltimo comando a enviar (coalescing)."""
        self.last_command_time = time.time()
        # Actividad: mantener polling rÃ¡pido para reflejar cambios
        try:
            self._active_until = max(self._active_until, time.time() + 2.5)
            if self._adaptive_polling_enabled:
                self.state_poll_interval = float(self._state_poll_min_interval_s)
        except Exception:
            pass
        if not self.bulbs:
            return
        with self._pending_pilots_lock:
            if ip:
                self._pending_pilots_by_ip[str(ip)] = pilot
            else:
                self._pending_pilot_global = pilot

    async def _flush_pending_pilots(self) -> None:
        """EnvÃ­a el Ãºltimo comando por bombilla/global en un solo batch."""
        if not self.bulbs:
            return

        with self._pending_pilots_lock:
            pilot_global = self._pending_pilot_global
            pilots_by_ip = dict(self._pending_pilots_by_ip)
            self._pending_pilot_global = None
            self._pending_pilots_by_ip.clear()

        if pilot_global is None and not pilots_by_ip:
            return

        tasks = []
        for bulb in list(self.bulbs):
            bulb_ip = getattr(bulb, "ip", None)
            if not bulb_ip:
                continue
            pilot = pilots_by_ip.get(bulb_ip) or pilot_global
            if pilot is None:
                continue
            tasks.append(bulb.turn_on(pilot))

        if not tasks:
            return

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            # Red puede fallar; no spamear logs.
            pass

    def _add_bulb_by_ip(self, ip):
        async def _f():
            if not any(b.ip == ip for b in self.bulbs):
                try:
                    self.bulbs.append(wizlight(ip))
                except Exception:
                    self.logger.exception(f"No se pudo crear wizlight({ip})")
        if self.loop.is_running(): asyncio.run_coroutine_threadsafe(_f(), self.loop)

    async def _discover_bulbs(self):
        try:
            found = await discovery.discover_lights(broadcast_space="255.255.255.255")
            for b in found:
                if not any(x.ip == b.ip for x in self.bulbs):
                    self.bulbs.append(b)
                    self.bulbs_manager.add_bulb({"ip": b.ip, "mac": b.mac})

            # xito: reset backoff (mantener mÃ­nimo)
            self._discovery_fails = 0
            self._discovery_next_ts = time.time() + float(self._discovery_min_interval_s)
        except Exception:
            self.logger.exception("Error descubriendo bombillas")

            # Falla: backoff exponencial, cap
            try:
                self._discovery_fails += 1
                backoff = float(self._discovery_min_interval_s) * (2 ** min(self._discovery_fails, 4))
                backoff = min(float(self._discovery_backoff_max_s), backoff)
                self._discovery_next_ts = time.time() + backoff
            except Exception:
                self._discovery_next_ts = time.time() + float(self._discovery_min_interval_s)

    async def _poll_bulb_states(self) -> None:
        """Actualiza cache de estado por bombilla (no toca UI)."""
        if self._polling_paused:
            return
        if time.time() < self._interaction_until:
            return
        if not self.bulbs:
            return

        now = time.time()
        changed_any = False

        for bulb in list(self.bulbs):
            ip = getattr(bulb, "ip", None)
            if not ip:
                continue

            # Backoff por IP: si fallÃ³ recientemente, saltea hasta next_poll_ts
            try:
                rec = self._poll_backoff.get(ip)
                if isinstance(rec, dict) and now < float(rec.get("next", 0.0)):
                    continue
            except Exception:
                pass
            try:
                await bulb.updateState()
                state: PilotParser | None = getattr(bulb, "state", None)
                if state is None:
                    raise RuntimeError("Estado vacÃ­o")

                bri_255 = state.get_brightness()
                bri = None
                if bri_255 is not None:
                    try:
                        bri = int(max(0, min(100, round((float(bri_255) / 255.0) * 100))))
                    except Exception:
                        bri = None

                st = {
                    "reachable": True,
                    "state": bool(state.get_state()) if state.get_state() is not None else None,
                    "brightness": bri,
                    "temp": state.get_colortemp(),
                    "rgb": state.get_rgb(),
                    "sceneId": state.get_scene_id(),
                    "updated_at": time.time(),
                }

                # Detectar cambios (sin depender de updated_at)
                try:
                    with self._bulb_states_lock:
                        prev = self._bulb_states.get(ip) or {}
                    prev_sig = {
                        "reachable": prev.get("reachable"),
                        "state": prev.get("state"),
                        "brightness": prev.get("brightness"),
                        "temp": prev.get("temp"),
                        "rgb": prev.get("rgb"),
                        "sceneId": prev.get("sceneId"),
                    }
                    cur_sig = {
                        "reachable": st.get("reachable"),
                        "state": st.get("state"),
                        "brightness": st.get("brightness"),
                        "temp": st.get("temp"),
                        "rgb": st.get("rgb"),
                        "sceneId": st.get("sceneId"),
                    }
                    if cur_sig != prev_sig:
                        changed_any = True
                except Exception:
                    changed_any = True

                # xito: reset backoff
                self._poll_backoff[ip] = {"fails": 0, "next": now + float(self.state_poll_interval)}
            except Exception:
                # No spamear logs por red: sÃ³lo debug.
                self.logger.debug(f"No se pudo leer estado de {ip}")
                st = {
                    "reachable": False,
                    "updated_at": time.time(),
                }

                # Si antes era reachable, cuenta como cambio
                try:
                    with self._bulb_states_lock:
                        prev = self._bulb_states.get(ip) or {}
                    if bool(prev.get("reachable", True)) is True:
                        changed_any = True
                except Exception:
                    pass

                # Falla: aumentar backoff progresivo (cap configurable)
                try:
                    rec = self._poll_backoff.get(ip) or {}
                    fails = int(rec.get("fails", 0)) + 1
                    # 2, 4, 8, 16, 30...
                    backoff_s = min(float(self._poll_backoff_max_s), float(self._poll_backoff_base_s) * (2 ** min(fails, 4)))
                    self._poll_backoff[ip] = {"fails": fails, "next": now + backoff_s}
                except Exception:
                    self._poll_backoff[ip] = {"fails": 1, "next": now + 4.0}

            with self._bulb_states_lock:
                self._bulb_states[ip] = st

        # Ajuste adaptativo (al final del sweep)
        if self._adaptive_polling_enabled and not self._polling_paused:
            try:
                if now < self._active_until:
                    self.state_poll_interval = float(self._state_poll_min_interval_s)
                    self._last_change_ts = now
                elif changed_any:
                    self.state_poll_interval = float(self._state_poll_min_interval_s)
                    self._last_change_ts = now
                else:
                    idle_for = now - float(self._last_change_ts)
                    if idle_for >= float(self._state_poll_idle_after_s):
                        self.state_poll_interval = min(
                            float(self._state_poll_max_interval_s),
                            max(
                                float(self._state_poll_min_interval_s),
                                float(self.state_poll_interval) * float(self._state_poll_growth_factor),
                            ),
                        )
                    else:
                        self.state_poll_interval = float(self._state_poll_min_interval_s)
            except Exception:
                pass

    def _start_background_loop(self):
        asyncio.set_event_loop(self.loop)
        self._loop_ready.set()
        self.loop.create_task(self._monitor())
        self.loop.create_task(self._command_worker())
        self.loop.run_forever()

    async def _command_worker(self):
        """EnvÃ­a comandos coalesced a ~10Hz para evitar colas/latencia."""
        while self.running:
            # Dormir adaptativo: si no hay comandos pendientes, no despiertes 10 veces por segundo.
            try:
                with self._pending_pilots_lock:
                    has_pending = bool(self._pending_pilot_global) or bool(self._pending_pilots_by_ip)
            except Exception:
                has_pending = True

            if has_pending:
                try:
                    await self._flush_pending_pilots()
                except Exception:
                    pass
                await asyncio.sleep(float(self._command_active_sleep_s))
            else:
                await asyncio.sleep(float(self._command_idle_sleep_s))

    async def _monitor(self):
        while self.running:
            now = time.time()
            if now - self._last_state_poll > self.state_poll_interval:
                self._last_state_poll = now
                try:
                    await self._poll_bulb_states()
                except Exception:
                    self.logger.exception("Error en polling de estados")

            # Dormir adaptativo: ahorra CPU cuando estÃ¡ en pausa o no hay bombillas.
            if self._polling_paused:
                sleep_s = 2.0
            elif not self.bulbs:
                sleep_s = float(self._monitor_no_bulbs_sleep_s)
            else:
                sleep_s = 1.0

            await asyncio.sleep(sleep_s)
