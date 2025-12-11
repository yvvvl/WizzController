import asyncio
import logging
import threading
import sys
import time
from typing import List, Callable, Optional, Dict, Any

from pywizlight import wizlight, PilotBuilder, discovery
from config.bulbs_manager import BulbsManager

try:
    from core.event_bus import EventBus
except ImportError:
    EventBus = None

class LightController:
    def __init__(self, event_bus=None):
        self.bulbs_manager = BulbsManager()
        self.bulbs: List[wizlight] = []
        self.callback: Optional[Callable] = None
        self.event_bus = event_bus
        
        self.running = True
        self.last_command_time = 0
        self.monitor_cooldown = 2.0
        
        self._current_state = {
            "state": False,
            "brightness": 100,
            "temp": 2700,
            "rgb": (0, 0, 0),
            "sceneId": 0,
            "speed": 100
        }
        
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = asyncio.new_event_loop()

        self.thread = threading.Thread(target=self._start_background_loop, daemon=True)
        self.thread.start()

    def start(self):
        print("[LightController] Iniciando servicios...")
        known = self.bulbs_manager.get_bulbs()
        for ip in known: self._add_bulb_by_ip(ip)
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._discover_bulbs(), self.loop)

    def set_callback(self, callback: Callable):
        self.callback = callback

    def turn_on(self):
        self._update_local(state=True)
        # Al encender sin params, restauramos el último estado
        self._send_command(PilotBuilder(state=True))

    def turn_off(self):
        """Método de apagado reforzado"""
        self._update_local(state=False)
        self.last_command_time = time.time()
        
        if not self.bulbs: return

        async def _off():
            for bulb in self.bulbs:
                try: 
                    # Usamos el método nativo turn_off de la librería para mayor seguridad
                    await bulb.turn_off()
                except Exception as e: 
                    logging.error(f"Error apagando {bulb.ip}: {e}")
        
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_off(), self.loop)

    def toggle(self):
        if self._current_state["state"]: self.turn_off()
        else: self.turn_on()

    def set_rgb(self, r, g, b):
        self._update_local(state=True, rgb=(r,g,b))
        self._send_command(PilotBuilder(rgb=(r, g, b)))

    def set_white(self, kelvin):
        k = max(2200, min(6500, kelvin))
        self._update_local(state=True, temp=k)
        self._send_command(PilotBuilder(colortemp=k))

    def set_brightness(self, intensity):
        val = max(10, min(100, intensity))
        self._update_local(brightness=val)
        wiz_val = int((val / 100) * 255)
        self._send_command(PilotBuilder(brightness=wiz_val))

    def set_scene(self, scene_id):
        self._update_local(state=True, sceneId=scene_id)
        self._send_command(PilotBuilder(scene=scene_id))

    def get_state(self):
        return self._current_state

    def _update_local(self, **kwargs):
        self._current_state.update(kwargs)
        if self.callback: 
            try: self.callback(self._current_state)
            except: pass
        if self.event_bus:
            self.event_bus.emit("light_state_changed", self._current_state)

    def _send_command(self, pilot):
        self.last_command_time = time.time()
        if not self.bulbs: return
        async def _send():
            for bulb in self.bulbs:
                try: await bulb.turn_on(pilot)
                except: pass
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), self.loop)

    def _add_bulb_by_ip(self, ip):
        async def _f():
            if not any(b.ip == ip for b in self.bulbs):
                try: self.bulbs.append(wizlight(ip))
                except: pass
        if self.loop.is_running(): asyncio.run_coroutine_threadsafe(_f(), self.loop)

    async def _discover_bulbs(self):
        try:
            found = await discovery.discover_lights(broadcast_space="255.255.255.255")
            for b in found:
                if not any(x.ip == b.ip for x in self.bulbs):
                    self.bulbs.append(b)
                    self.bulbs_manager.add_bulb({"ip": b.ip, "mac": b.mac})
        except: pass

    def _start_background_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._monitor())
        self.loop.run_forever()

    async def _monitor(self):
        while self.running:
            if time.time() - self.last_command_time > self.monitor_cooldown:
                # Lógica de polling (opcional)
                pass 
            await asyncio.sleep(2.0)