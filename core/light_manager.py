import asyncio
import logging
from pywizlight import wizlight, PilotBuilder
from core.discovery import BulbDiscovery
from typing import Dict, List, Optional

class LightManager:
    """
    Gestor principal de bombillas WiZ. Permite controlar encendido, apagado, color, brillo y temperatura.
    """
    def __init__(self) -> None:
        # Ensure compatibility with Windows event loop
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.bulbs: Dict[str, wizlight] = {}
        self.active_bulb_id: Optional[str] = None
        self.selected_bulb: Optional[Dict[str, Any]] = None
        self.bulbs_list: List[Dict[str, Any]] = []


    async def discover_bulbs(self, timeout: int = 3) -> list[dict]:
        """
        Descubre bombillas WiZ en la red local (async).
        Args:
            timeout (int): Tiempo de espera en segundos.
        Returns:
            list[dict]: Lista de bombillas encontradas.
        """
        return await discovery.discover_lights(broadcast_space="192.168.1.255")

    def discover_bulbs(self) -> list[dict]:
        """
        Descubre bombillas WiZ en la red local (sync).
        Returns:
            list[dict]: Lista de bombillas encontradas.
        """
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            bulbs = new_loop.run_until_complete(BulbDiscovery.discover_bulbs())
            new_loop.close()
        except Exception as e:
            logging.error(f"Error en discover_bulbs: {e}")
            bulbs = []
        return bulbs

    def register_bulb(self, bulb_id: str, ip: str) -> None:
        """
        Registra una bombilla por su ID e IP.
        """
        try:
            # Ensure the asyncio event loop is set
            asyncio.set_event_loop(self.loop)
            self.bulbs[bulb_id] = wizlight(ip)
            if not self.active_bulb_id:
                self.active_bulb_id = bulb_id
        except Exception as e:
            logging.error(f"Error registering bulb {bulb_id}: {e}")

    def set_active_bulb(self, bulb_id: str) -> None:
        """
        Selecciona la bombilla activa por su ID.
        """
        if bulb_id in self.bulbs:
            self.active_bulb_id = bulb_id

    def _get_active_bulb(self) -> str | None:
        """
        Devuelve la IP de la bombilla seleccionada.
        Returns:
            str | None: IP de la bombilla o None si no hay seleccionada.
        """
        if hasattr(self, 'selected_bulb') and self.selected_bulb:
            ip = self.selected_bulb.get('ip')
            if ip:
                # Crear bulb solo cuando se va a usar, dentro de un event loop
                return ip
        return None

    def set_selected_bulb(self, bulb: dict) -> None:
        self.selected_bulb = bulb

    async def turn_on(self) -> None:
        """
        Enciende la bombilla activa.
        """
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on()
            logging.info(f"Encendiendo bombilla: {self.selected_bulb}")

    async def turn_off(self) -> None:
        """
        Apaga la bombilla activa.
        """
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_off()
            logging.info(f"Apagando bombilla: {self.selected_bulb}")

    async def set_brightness(self, brightness: int) -> None:
        """
        Ajusta el brillo de la bombilla activa (0-100).
        """
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on(PilotBuilder(brightness=brightness))
            logging.info(f"Brillo {brightness} para bombilla: {self.selected_bulb}")

    async def set_color(self, r: int, g: int, b: int) -> None:
        """
        Ajusta el color RGB de la bombilla activa.
        """
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on(PilotBuilder(rgb=(r, g, b)))
            logging.info(f"Color {(r, g, b)} para bombilla: {self.selected_bulb}")

    async def set_temperature(self, kelvin: int) -> None:
        """
        Ajusta la temperatura de color de la bombilla activa.
        """
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on(PilotBuilder(colortemp=kelvin))
            logging.info(f"Temperatura {kelvin} para bombilla: {self.selected_bulb}")

    def turn_on(self) -> None:
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                await bulb.turn_on()
            asyncio.run(do())
            logging.info("Bombilla encendida")
        else:
            logging.warning("No hay bombilla seleccionada")

    def turn_off(self) -> None:
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                await bulb.turn_off()
            asyncio.run(do())
            logging.info("Bombilla apagada")
        else:
            logging.warning("No hay bombilla seleccionada")

    def set_color(self, rgb):
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                pilot = PilotBuilder(rgb=rgb)
                await bulb.turn_on(pilot)
            asyncio.run(do())
            logging.info(f"Color establecido: {rgb}")
        else:
            logging.warning("No hay bombilla seleccionada")

    def set_brightness(self, brightness):
        ip = self._get_active_bulb()
        if ip:
            # WiZ bulbs typically use brightness 10-255
            min_brightness = 10
            max_brightness = 255
            # Map 0-100 slider to 10-255
            value = int(min_brightness + (max_brightness - min_brightness) * (brightness / 100))
            value = max(min_brightness, min(max_brightness, value))
            async def do():
                bulb = wizlight(ip)
                pilot = PilotBuilder(brightness=value)
                await bulb.turn_on(pilot)
            asyncio.run(do())
            logging.info(f"Brillo establecido: {value} (slider: {brightness})")
        else:
            logging.warning("No hay bombilla seleccionada")

    def set_temperature(self, kelvin):
        ip = self._get_active_bulb()
        if ip:
            # Clamp temperature to bulb range (2200K-6500K)
            kelvin = max(2200, min(6500, kelvin))
            async def do():
                bulb = wizlight(ip)
                pilot = PilotBuilder(colortemp=kelvin)
                await bulb.turn_on(pilot)
            asyncio.run(do())
            logging.info(f"Temperatura establecida: {kelvin}")
        else:
            logging.warning("No hay bombilla seleccionada")

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