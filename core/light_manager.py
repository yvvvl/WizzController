import asyncio
import logging
import threading
import sys
import time
from typing import List, Callable, Optional
from pywizlight import wizlight, PilotBuilder, discovery
from config.bulbs_manager import BulbsManager

class LightManager:
    def __init__(self):
        self.bulbs_manager = BulbsManager()
        self.bulbs: List[wizlight] = []
        self.callback: Optional[Callable] = None
        self.running = True
        
        self.last_command_time = 0
        self.monitor_cooldown = 1.5
        
        # Cache de estado
        self._current_state = {
            "state": False,
            "brightness": 100,
            "temp": 2700,
            "rgb": (0, 0, 0),
            "sceneId": 0,
            "speed": 100
        }
        
        # Loop de eventos
        if sys.platform == 'win32':
            self.loop = asyncio.SelectorEventLoop()
        else:
            self.loop = asyncio.new_event_loop()

        self.thread = threading.Thread(target=self._start_background_loop, daemon=True)
        self.thread.start()

    def _start_background_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._state_monitor())
        self.loop.run_forever()

    def set_callback(self, callback: Callable):
        self.callback = callback

    def get_state(self):
        return self._current_state

    def _notify_ui(self):
        if self.callback:
            self.callback(self._current_state)

    async def _state_monitor(self):
        print("Monitor de estado iniciado")
        while self.running:
            if time.time() - self.last_command_time < self.monitor_cooldown:
                await asyncio.sleep(0.5)
                continue

            if self.bulbs:
                try:
                    target_bulb = self.bulbs[0]
                    state = await target_bulb.updateState()
                    
                    if state:
                        is_on = state.get_state()
                        
                        raw_bri = state.get_brightness()
                        if raw_bri is None: raw_bri = 0
                        brightness_pct = int((raw_bri / 255) * 100) if is_on else 0
                        
                        temp = state.get_colortemp() or 0
                        
                        # Corrección RGB: Convertir None a 0
                        rgb = state.get_rgb()
                        if rgb is None or any(c is None for c in rgb):
                            rgb = (0, 0, 0)
                            
                        scene_id = state.get_scene_id() or 0
                        
                        # Recuperar velocidad
                        speed = state.get_speed() or 100

                        self._current_state = {
                            "state": is_on,
                            "brightness": brightness_pct,
                            "temp": temp,
                            "rgb": rgb,
                            "sceneId": scene_id,
                            "speed": speed
                        }
                        self._notify_ui()
                            
                except Exception as e:
                    pass 
            
            await asyncio.sleep(2.0)

    # --- COMANDOS ---

    def turn_on(self):
        self._current_state["state"] = True
        self._notify_ui()
        self._send_command(PilotBuilder(state=True))

    def turn_off(self):
        self._current_state["state"] = False
        self._notify_ui()
        self.last_command_time = time.time()
        
        if not self.bulbs: return

        async def _off():
            for bulb in self.bulbs:
                try:
                    await bulb.turn_off()
                except Exception as e:
                    logging.error(f"Error al apagar {bulb.ip}: {e}")

        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_off(), self.loop)

    def set_rgb(self, r: int, g: int, b: int):
        self._current_state["rgb"] = (r, g, b)
        self._send_command(PilotBuilder(rgb=(r, g, b)))

    def set_white(self, kelvin: int):
        kelvin = max(2200, min(6500, kelvin))
        self._current_state["temp"] = kelvin
        self._send_command(PilotBuilder(colortemp=kelvin))

    def set_brightness(self, intensity: int):
        self._current_state["brightness"] = intensity
        self._notify_ui() 
        wiz_value = int(intensity * 2.55)
        wiz_value = max(25, min(255, wiz_value))
        self._send_command(PilotBuilder(brightness=wiz_value))

    def set_scene(self, scene_id: int):
        self._current_state["sceneId"] = scene_id
        # Reset de velocidad al cambiar escena
        self._current_state["speed"] = 100
        self._send_command(PilotBuilder(scene=scene_id))
        
    def set_speed(self, speed: int):
        """Ajusta velocidad (10-200) enviando también la escena actual"""
        speed = max(10, min(200, speed))
        self._current_state["speed"] = speed
        current_scene = self._current_state.get("sceneId", 0)
        
        # Solo aplicar velocidad si hay una escena dinámica activa
        if current_scene > 0:
            print(f"Set Speed: {speed}% for Scene {current_scene}")
            self._send_command(PilotBuilder(scene=current_scene, speed=speed))

    def _send_command(self, pilot: PilotBuilder):
        self.last_command_time = time.time()
        if not self.bulbs: return

        async def _send():
            for bulb in self.bulbs:
                try:
                    await bulb.turn_on(pilot)
                except Exception as e:
                    logging.error(f"Error comando {bulb.ip}: {e}")

        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), self.loop)

    # --- SETUP ---
    def startup_sequence(self):
        print("Iniciando LightManager...")
        known_bulbs = self.bulbs_manager.get_bulbs()
        for ip in known_bulbs:
            self._add_bulb_by_ip(ip)
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._discover_bulbs(), self.loop)

    def _add_bulb_by_ip(self, ip: str):
        async def _add():
            if not any(b.ip == ip for b in self.bulbs):
                try:
                    bulb = wizlight(ip)
                    self.bulbs.append(bulb)
                except: pass
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_add(), self.loop)

    async def _discover_bulbs(self):
        try:
            found_bulbs = await discovery.discover_lights(broadcast_space="255.255.255.255")
            for bulb in found_bulbs:
                if not any(b.ip == bulb.ip for b in self.bulbs):
                    self.bulbs.append(bulb)
                    self.bulbs_manager.add_bulb({"ip": bulb.ip, "mac": bulb.mac})
        except Exception: pass