import asyncio
import logging
import math
from pywizlight import wizlight, PilotBuilder
from core.discovery import BulbDiscovery
from typing import Dict, List, Optional, Any

class LightManager:
    """
    Gestor principal de bombillas WiZ. 
    Versión corregida: Sin context managers asíncronos para compatibilidad con pywizlight.
    """
    def __init__(self) -> None:
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
        self.bulbs: Dict[str, wizlight] = {}
        self.active_bulb_id: Optional[str] = None
        self.selected_bulb: Optional[Dict[str, Any]] = None
        
        self.last_rgb = (255, 255, 255)
        self.last_brightness = 100

    # --- Descubrimiento ---
    
    async def discover_bulbs_async(self, timeout: int = 3) -> list[dict]:
        return await BulbDiscovery.discover_bulbs(timeout=timeout)

    def discover_bulbs(self) -> list[dict]:
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            bulbs = new_loop.run_until_complete(BulbDiscovery.discover_bulbs())
            new_loop.close()
        except Exception as e:
            logging.error(f"Error en discover_bulbs: {e}")
            bulbs = []
        return bulbs

    # --- Gestión de Selección ---

    def register_bulb(self, bulb_id: str, ip: str) -> None:
        self.active_bulb_id = bulb_id
        
    def set_active_bulb(self, bulb_id: str) -> None:
        self.active_bulb_id = bulb_id

    def _get_active_bulb(self) -> str | None:
        if hasattr(self, 'selected_bulb') and self.selected_bulb:
            return self.selected_bulb.get('ip')
        return None

    def set_selected_bulb(self, bulb: dict) -> None:
        self.selected_bulb = bulb

    # --- Comandos Síncronos (UI) ---

    def turn_on(self) -> None:
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                await bulb.turn_on()
            asyncio.run(do())
            logging.info("Bombilla encendida")

    def turn_off(self) -> None:
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                await bulb.turn_off()
            asyncio.run(do())
            logging.info("Bombilla apagada")

    def toggle_light(self) -> None:
        """Alterna el estado de la bombilla (Toggle)."""
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                # Primero obtenemos el estado actual
                await bulb.updateState()
                if bulb.status:
                    await bulb.turn_off()
                else:
                    await bulb.turn_on()
            asyncio.run(do())
            logging.info("Bombilla alternada (Toggle)")
        else:
            logging.warning("No hay bombilla seleccionada para toggle")

    def set_color(self, rgb):
        self.last_rgb = rgb
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                pilot = PilotBuilder(rgb=rgb)
                await bulb.turn_on(pilot)
            asyncio.run(do())
            logging.info(f"Color establecido: {rgb}")

    def set_brightness(self, brightness):
        self.last_brightness = brightness
        ip = self._get_active_bulb()
        if ip:
            val = max(10, min(255, int(10 + (245 * (brightness / 100)))))
            async def do():
                bulb = wizlight(ip)
                pilot = PilotBuilder(brightness=val)
                await bulb.turn_on(pilot)
            asyncio.run(do())
            logging.info(f"Brillo establecido: {val}")

    def set_temperature(self, kelvin):
        ip = self._get_active_bulb()
        if ip:
            k = max(2200, min(6500, kelvin))
            async def do():
                bulb = wizlight(ip)
                pilot = PilotBuilder(colortemp=k)
                await bulb.turn_on(pilot)
            asyncio.run(do())
            logging.info(f"Temperatura establecida: {k}")

    def activate_scene(self, scene_id: int) -> None:
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                # IMPORTANTE: Usamos 'scene'
                await bulb.turn_on(PilotBuilder(scene=scene_id))
            asyncio.run(do())
            logging.info(f"Escena {scene_id} activada")

    # --- Comandos Asíncronos ---

    async def set_scene(self, scene_id: int) -> None:
        ip = self._get_active_bulb()
        if ip:
            bulb = wizlight(ip)
            await bulb.turn_on(PilotBuilder(scene=scene_id))

    def _kelvin_to_rgb(self, temp_kelvin):
        """Convierte temperatura de color (Kelvin) a RGB."""
        temp = temp_kelvin / 100.0
        if temp <= 66:
            red = 255
            green = 99.4708025861 * math.log(temp) - 161.1195681661
            blue = 0 if temp <= 19 else (138.5177312231 * math.log(temp - 10) - 305.0447927307)
        else:
            red = 329.698727446 * ((temp - 60) ** -0.1332047592)
            green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
            blue = 255

        def clamp(x):
            return max(0, min(255, int(x)))

        return clamp(red), clamp(green), clamp(blue)