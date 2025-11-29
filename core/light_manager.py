import asyncio
from pywizlight import wizlight, PilotBuilder
from core.discovery import BulbDiscovery

class LightManager:
    def __init__(self):
        # Ensure compatibility with Windows event loop
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.bulbs: Dict[str, wizlight] = {}
        self.active_bulb_id: Optional[str] = None
        self.selected_bulb = None  # Inicializa la bombilla seleccionada

    async def discover_bulbs(self, timeout: int = 3):
        """Discover bulbs on the network."""
        return await discovery.discover_lights(broadcast_space="192.168.1.255")

    def discover_bulbs(self):
        """Descubre ampolletas WiZ en la red usando pywizlight."""
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            bulbs = new_loop.run_until_complete(BulbDiscovery.discover_bulbs())
            new_loop.close()
        except Exception as e:
            print(f"Error en discover_bulbs: {e}")
            bulbs = []
        return bulbs

    def register_bulb(self, bulb_id: str, ip: str):
        """Register a bulb by its ID and IP address."""
        try:
            # Ensure the asyncio event loop is set
            asyncio.set_event_loop(self.loop)
            self.bulbs[bulb_id] = wizlight(ip)
            if not self.active_bulb_id:
                self.active_bulb_id = bulb_id
        except Exception as e:
            print(f"Error registering bulb {bulb_id}: {e}")

    def set_active_bulb(self, bulb_id: str):
        """Set the active bulb by its ID."""
        if bulb_id in self.bulbs:
            self.active_bulb_id = bulb_id

    def _get_active_bulb(self):
        """Devuelve la instancia wizlight de la ampolleta seleccionada."""
        if hasattr(self, 'selected_bulb') and self.selected_bulb:
            ip = self.selected_bulb.get('ip')
            if ip:
                # Crear bulb solo cuando se va a usar, dentro de un event loop
                return ip
        return None

    def set_selected_bulb(self, bulb):
        self.selected_bulb = bulb

    async def turn_on(self):
        """Turn on the active bulb."""
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on()

    async def turn_off(self):
        """Turn off the active bulb."""
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_off()

    async def set_brightness(self, brightness: int):
        """Set brightness of the active bulb (0-100)."""
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on(PilotBuilder(brightness=brightness))

    async def set_color(self, r: int, g: int, b: int):
        """Set RGB color of the active bulb."""
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on(PilotBuilder(rgb=(r, g, b)))

    async def set_temperature(self, kelvin: int):
        """Set color temperature of the active bulb."""
        bulb = self.bulbs.get(self.active_bulb_id)
        if bulb:
            await bulb.turn_on(PilotBuilder(colortemp=kelvin))

    def turn_on(self):
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                await bulb.turn_on()
            asyncio.run(do())
            print("Bombilla encendida")
        else:
            print("No hay bombilla seleccionada")

    def turn_off(self):
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                await bulb.turn_off()
            asyncio.run(do())
            print("Bombilla apagada")
        else:
            print("No hay bombilla seleccionada")

    def set_color(self, rgb):
        ip = self._get_active_bulb()
        if ip:
            async def do():
                bulb = wizlight(ip)
                pilot = PilotBuilder(rgb=rgb)
                await bulb.turn_on(pilot)
            asyncio.run(do())
            print(f"Color establecido: {rgb}")
        else:
            print("No hay bombilla seleccionada")

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
            print(f"Brillo establecido: {value} (slider: {brightness})")
        else:
            print("No hay bombilla seleccionada")

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
            print(f"Temperatura establecida: {kelvin}")
        else:
            print("No hay bombilla seleccionada")

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