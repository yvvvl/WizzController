"""
LightController v3 — nativo completo, sin pywizlight, sin bloqueos.

Escritura  -> raw UDP fire-and-forget, coalescido a 50ms (instantáneo).
Lectura    -> getPilot / getSystemConfig nativos (estado real + capacidades).
Discovery  -> registration broadcast.

Mantiene la cobertura "como la app del teléfono" pero el camino de control
nunca espera ACK. La lectura ocurre fuera del hot path (al arrancar y on-demand).

API pública (compatible con hotkeys/voz):
  turn_on, turn_off, toggle, set_brightness, set_rgb, set_white, set_scene,
  set_ratio, get_state, refresh, summary
"""
import asyncio
import logging
import threading

from config.bulbs_manager import BulbsManager
from core.wiz_protocol import WizProtocol, create_endpoint, get_local_ip, WIZ_PORT
from core.wiz_capabilities import Capabilities, from_module_name


class LightController:
    MIN_INTERVAL = 0.05   # 50ms entre envíos al arrastrar (suave, sin saturar)

    def __init__(self, event_bus=None) -> None:
        self.event_bus = event_bus
        self.bulbs_manager = BulbsManager()

        self.bulb_ips: set[str] = set(self.bulbs_manager.get_bulbs().keys())
        self.bulbs: dict[str, dict] = {}   # ip -> {"mac","caps","state"}

        self.running = True
        self.loop = asyncio.new_event_loop()
        self.proto: WizProtocol | None = None

        self._target: dict = {}
        self._mirror: dict = {"state": True, "dimming": 100}
        self._dirty = False
        self._callback = None

        self.thread = threading.Thread(target=self._run_loop, daemon=True)

    # ------------------------------------------------------------------ #
    #  Ciclo de vida
    # ------------------------------------------------------------------ #
    def set_callback(self, callback) -> None:
        self._callback = callback

    def start(self) -> None:
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self) -> None:
        self.running = False

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._setup())
        self.loop.run_forever()

    async def _setup(self) -> None:
        _, self.proto = await create_endpoint(self.loop)
        self.loop.create_task(self._pump())
        self.loop.create_task(self._discover())
        logging.info(f"[Light] Listo. Bombillas guardadas: {self.bulb_ips or '(ninguna)'}")

    # ------------------------------------------------------------------ #
    #  Escritura coalescida
    # ------------------------------------------------------------------ #
    async def _pump(self) -> None:
        while self.running:
            if self._dirty and self.proto:
                self._dirty = False
                self._broadcast(dict(self._target))
                await asyncio.sleep(self.MIN_INTERVAL)
            else:
                await asyncio.sleep(0.01)

    def _broadcast(self, params: dict) -> None:
        if not params or not self.proto:
            return
        for ip in list(self.bulb_ips):
            self.proto.send_pilot(ip, params)
        self._fire_callback()

    def _fire_callback(self) -> None:
        if self._callback:
            try:
                self._callback(self.get_state())
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Discovery + lectura de estado real y capacidades
    # ------------------------------------------------------------------ #
    async def _discover(self) -> None:
        try:
            local_ip = get_local_ip()
            for _ in range(3):
                self.proto.send_registration(local_ip)
                await asyncio.sleep(0.35)
            await asyncio.sleep(0.4)

            ips = set(self.proto.discovered.keys()) | set(self.bulb_ips)
            for ip in ips:
                await self._probe(ip)

            # Sembrar el espejo con el estado REAL de la primera bombilla viva
            for info in self.bulbs.values():
                st = info.get("state") or {}
                if "state" in st:
                    self._mirror["state"] = st["state"]
                if "dimming" in st:
                    self._mirror["dimming"] = st["dimming"]
                break

            logging.info(f"[Light] Bombillas activas: {len(self.bulbs)}")
            self._fire_callback()
        except Exception as e:
            logging.debug(f"[Light] discovery: {e}")

    async def _probe(self, ip: str) -> None:
        sysc = await self.proto.query(ip, "getSystemConfig", self.loop, 1.0)
        pilot = await self.proto.query(ip, "getPilot", self.loop, 1.0)
        if sysc is None and pilot is None and ip not in self.bulb_ips:
            return  # inalcanzable

        module = (sysc or {}).get("moduleName")
        mac = (sysc or {}).get("mac") or self.proto.discovered.get(ip, {}).get("mac")
        caps = from_module_name(module)

        self.bulbs[ip] = {"mac": mac, "caps": caps, "state": pilot or {}}
        self.bulb_ips.add(ip)
        self.bulbs_manager.add_bulb({"ip": ip, "mac": mac, "port": WIZ_PORT})

    async def _refresh_async(self) -> None:
        for ip in list(self.bulb_ips):
            pilot = await self.proto.query(ip, "getPilot", self.loop, 1.0)
            if pilot and ip in self.bulbs:
                self.bulbs[ip]["state"] = pilot
        self._fire_callback()

    def refresh(self) -> None:
        """Relee el estado real de las bombillas (on-demand, no bloquea la UI)."""
        if self.proto:
            asyncio.run_coroutine_threadsafe(self._refresh_async(), self.loop)

    # ------------------------------------------------------------------ #
    #  API pública (control)
    # ------------------------------------------------------------------ #
    def _mark(self) -> None:
        self._mirror.update(self._target)
        self._dirty = True

    def set_rgb(self, r: int, g: int, b: int) -> None:
        self._target.update({"state": True, "r": int(r), "g": int(g), "b": int(b)})
        for k in ("temp", "sceneId", "speed"):
            self._target.pop(k, None)
        self._mark()

    def set_white(self, kelvin: int) -> None:
        self._target.update({"state": True, "temp": int(kelvin)})
        for k in ("r", "g", "b", "sceneId", "speed"):
            self._target.pop(k, None)
        self._mark()

    def set_scene(self, scene_id: int, speed: int | None = None) -> None:
        self._target.update({"state": True, "sceneId": int(scene_id)})
        if speed is not None:
            self._target["speed"] = int(max(20, min(200, speed)))
        for k in ("r", "g", "b", "temp"):
            self._target.pop(k, None)
        self._mark()

    def set_ratio(self, ratio: int) -> None:
        """Dispositivos de doble zona (0-100)."""
        self._target["ratio"] = int(max(0, min(100, ratio)))
        self._mark()

    def set_brightness(self, pct: int) -> None:
        self._target["dimming"] = int(max(10, min(100, pct)))   # dimming local es 0-100
        self._mark()

    def turn_on(self) -> None:
        self._target["state"] = True
        self._mark()

    def turn_off(self) -> None:
        self._target["state"] = False
        self._mark()

    def toggle(self) -> None:
        self.turn_off() if self._mirror.get("state", True) else self.turn_on()

    def get_state(self) -> dict:
        return dict(self._mirror)

    # ------------------------------------------------------------------ #
    #  Capacidades agregadas (para la UI)
    # ------------------------------------------------------------------ #
    def summary(self) -> dict:
        caps = [b["caps"] for b in self.bulbs.values()]
        if any(c.rgb for c in caps):
            label = "RGB + Blancos"
        elif any(c.tunable_white for c in caps):
            label = "Blancos"
        elif caps:
            label = "Regulable"
        else:
            label = ""
        return {"count": len(self.bulb_ips), "active": len(self.bulbs), "label": label}

    def supports_color(self) -> bool:
        return any(b["caps"].rgb for b in self.bulbs.values()) or not self.bulbs
