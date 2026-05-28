import asyncio
import logging
import threading
import time
from typing import Optional, Callable
from pywizlight import wizlight, PilotBuilder, discovery

class LightController:
    def __init__(self, event_bus=None):
        self.SEND_INTERVAL = 0.15  # Freno para no saturar la red
        self.bulbs = []
        self.running = True
        self.loop = asyncio.new_event_loop()
        self.event_bus = event_bus
        
        self._target_state = {} 
        self._last_sent_time = 0
        self._pending_update = False
        self._callback = None
        
        self.thread = threading.Thread(target=self._background_worker, daemon=True)
        # No iniciamos el thread aquí, esperamos a start()

    def set_callback(self, callback):
        self._callback = callback

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._discover_bulbs(), self.loop)

    def _background_worker(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._process_command_queue())
        self.loop.run_forever()

    async def _process_command_queue(self):
        while self.running:
            now = time.time()
            if self._pending_update and (now - self._last_sent_time >= self.SEND_INTERVAL):
                await self._sync_bulbs()
                self._pending_update = False
                self._last_sent_time = time.time()
            await asyncio.sleep(0.05)

    async def _sync_bulbs(self):
        if not self.bulbs: return
        
        pilot_args = {}
        t = self._target_state
        
        if "state" in t: pilot_args["state"] = t["state"]
        if "brightness" in t: pilot_args["brightness"] = int((t["brightness"] / 100) * 255)
        if "rgb" in t: pilot_args["rgb"] = t["rgb"]
        if "temp" in t: pilot_args["colortemp"] = t["temp"]
        if "sceneId" in t: pilot_args["scene"] = t["sceneId"]

        if not pilot_args: return

        pilot = PilotBuilder(**pilot_args)
        for bulb in self.bulbs:
            try:
                await bulb.turn_on(pilot)
            except Exception as e:
                logging.error(f"Error enviando a {bulb.ip}: {e}")

    # --- MÉTODOS PÚBLICOS ---
    def set_rgb(self, r, g, b):
        self._target_state["state"] = True
        self._target_state["rgb"] = (r, g, b)
        self._target_state.pop("temp", None)
        self._target_state.pop("sceneId", None)
        self._pending_update = True

    def set_brightness(self, intensity):
        self._target_state["brightness"] = max(10, min(100, intensity))
        self._pending_update = True

    def set_white(self, kelvin):
        self._target_state["state"] = True
        self._target_state["temp"] = kelvin
        self._target_state.pop("rgb", None)
        self._target_state.pop("sceneId", None)
        self._pending_update = True
        
    def set_scene(self, scene_id):
        self._target_state["state"] = True
        self._target_state["sceneId"] = scene_id
        self._target_state.pop("rgb", None)
        self._target_state.pop("temp", None)
        self._pending_update = True

    def turn_off(self):
        self._target_state["state"] = False
        self._pending_update = True

    def turn_on(self):
        self._target_state["state"] = True
        self._pending_update = True

    async def _discover_bulbs(self):
        try:
            print("🔍 Buscando bombillas WiZ...")
            found = await discovery.discover_lights(broadcast_space="255.255.255.255")
            for b in found:
                if not any(x.ip == b.ip for x in self.bulbs):
                    print(f"💡 Bombilla encontrada: {b.ip}")
                    self.bulbs.append(b)
        except Exception as e:
            print(f"Error discovery: {e}")