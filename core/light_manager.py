import asyncio
import logging
from typing import Dict, Optional, Any

from pywizlight import wizlight, PilotBuilder

from core.discovery import BulbDiscovery
from config.bulbs_manager import BulbsManager


class LightManager:
    """
    Gestor principal de bombillas WiZ con persistencia de conexión y
    API amigable para la UI (color, brillo, temperatura, escenas).
    """

    def __init__(self) -> None:
        # Maneja el archivo config/json/bulbs.json
        self.bulbs_manager = BulbsManager()

        # Bombilla seleccionada actualmente (dict con al menos "ip" y "mac")
        self.selected_bulb: Optional[Dict[str, Any]] = None

        # Último color/brillo usados (para mantener consistencia)
        self.last_rgb: tuple[int, int, int] = (255, 255, 255)
        self.last_brightness: int = 100

    # ------------------------------------------------------------------
    #  LÓGICA DE INICIO
    # ------------------------------------------------------------------
    def startup_sequence(self) -> None:
        """
        Intenta reconectar a una bombilla guardada.
        Si no hay o no responde, escanea la red.
        """
        logging.info("Iniciando secuencia de arranque...")
        saved_bulbs = self.bulbs_manager.get_bulbs()

        if saved_bulbs:
            for ip, bulb_data in saved_bulbs.items():
                logging.info(f"Intentando reconexión rápida a: {ip}")
                if self._check_connection(ip):
                    self._remember_bulb(bulb_data)
                    logging.info(f"⚡ Conexión rápida exitosa a {ip}")
                    return
                else:
                    logging.warning(f"La IP guardada {ip} no responde.")

        logging.info("Iniciando escaneo de red...")
        self.scan_and_register()

    def _check_connection(self, ip: str) -> bool:
        """
        Devuelve True si la bombilla en esa IP responde al updateState().
        """
        async def check():
            try:
                bulb = wizlight(ip)
                await bulb.updateState()
                return True
            except Exception as e:
                logging.error(f"Error comprobando conexión con {ip}: {e}")
                return False

        try:
            return asyncio.run(check())
        except Exception as e:
            logging.error(f"Error general comprobando conexión con {ip}: {e}")
            return False

    # ------------------------------------------------------------------
    #  DISCOVERY / REGISTRO
    # ------------------------------------------------------------------
    def scan_and_register(self) -> None:
        """
        Escanea la red en busca de bombillas WiZ y registra la primera.
        """
        try:
            bulbs = asyncio.run(BulbDiscovery.discover_bulbs())
        except Exception as e:
            logging.error(f"Error escaneando bombillas: {e}")
            bulbs = []

        if bulbs:
            first_bulb = bulbs[0]
            ip = first_bulb.get("ip")
            if ip:
                self._remember_bulb(first_bulb)
                logging.info(f"Bombilla descubierta y registrado: {ip}")
        else:
            logging.warning("No se encontraron bombillas WiZ en el escaneo.")

    def _remember_bulb(self, bulb: Dict[str, Any]) -> None:
        """
        Actualiza la bombilla seleccionada y la guarda en BulbsManager.
        Espera un diccionario con al menos la clave "ip".
        """
        self.selected_bulb = bulb
        try:
            self.bulbs_manager.add_bulb(bulb)
        except Exception as e:
            logging.error(f"No se pudo guardar la bombilla en BulbsManager: {e}")

    # ------------------------------------------------------------------
    #  HELPERS INTERNOS
    # ------------------------------------------------------------------
    def _get_active_bulb(self) -> Optional[str]:
        """
        Devuelve la IP de la bombilla activa.

        - Si hay una seleccionada en memoria, se usa esa.
        - Si no, se intenta usar la primera del archivo bulbs.json.
        """
        if self.selected_bulb and self.selected_bulb.get("ip"):
            return self.selected_bulb["ip"]

        bulbs = self.bulbs_manager.get_bulbs()
        if bulbs:
            ip, bulb = next(iter(bulbs.items()))
            self.selected_bulb = bulb
            return ip

        logging.warning("No hay bombilla activa disponible.")
        return None

    def set_selected_bulb(self, bulb: Dict[str, Any]) -> None:
        """
        Permite a la UI establecer explícitamente la bombilla seleccionada.
        """
        self._remember_bulb(bulb)

    def _run_async(self, coro) -> None:
        """
        Ejecuta una corrutina de forma segura desde el contexto de la UI.
        """
        try:
            asyncio.run(coro)
        except RuntimeError:
            # Si ya hay un loop corriendo (poco probable en PyQt puro),
            # se lanza como tarea.
            asyncio.create_task(coro)
        except Exception as e:
            logging.error(f"Error ejecutando tarea async: {e}")

    # ------------------------------------------------------------------
    #  ACCIONES DE POTENCIA (ENCENDER / APAGAR / TOGGLE)
    # ------------------------------------------------------------------
    def toggle(self) -> None:
        """Alterna el estado de la bombilla (ON <-> OFF)."""
        ip = self._get_active_bulb()
        if not ip:
            return

        async def do():
            bulb = wizlight(ip)
            await bulb.updateState()
            is_on = bulb.state.get_state()
            if is_on:
                await bulb.turn_off()
                logging.info("Toggle: Luz APAGADA")
            else:
                await bulb.turn_on()
                logging.info("Toggle: Luz ENCENDIDA")

        self._run_async(do())

    def turn_on(self) -> None:
        """Enciende la bombilla activa."""
        ip = self._get_active_bulb()
        if not ip:
            return

        async def do():
            await wizlight(ip).turn_on()

        self._run_async(do())
        logging.info("Bombilla ENCENDIDA")

    def turn_off(self) -> None:
        """Apaga la bombilla activa."""
        ip = self._get_active_bulb()
        if not ip:
            return

        async def do():
            await wizlight(ip).turn_off()

        self._run_async(do())
        logging.info("Bombilla APAGADA")

    # ------------------------------------------------------------------
    #  COLOR / BRILLO / TEMPERATURA / ESCENAS
    # ------------------------------------------------------------------
    def set_color(self, rgb: tuple[int, int, int]) -> None:
        """Cambia el color actual (modo RGB) y recuerda el último color.
        
        Regla especial para el picker:
        - Si el color es (0, 0, 0) lo interpretamos como
          "Brillo del selector de color = 0%" y apagamos la bombilla.
        """
        ip = self._get_active_bulb()
        if not ip:
            return

        async def do():
            bulb = wizlight(ip)

            # Si el selector de color manda negro absoluto, lo interpretamos
            # como brillo 0% del picker → apagamos en vez de mandar rgb=(0,0,0).
            if rgb == (0, 0, 0):
                await bulb.turn_off()
                logging.info("Color (0,0,0) → bombilla APAGADA (brillo picker 0%)")
                return

            # Cualquier otro color se aplica normalmente.
            self.last_rgb = rgb
            await bulb.turn_on(PilotBuilder(rgb=rgb))

        self._run_async(do())

    def _brightness_to_wiz(self, brightness: int) -> int:
        """Convierte 0–100% a un rango seguro de brillo para WiZ (10–255).

        Evitamos mandar 0 porque en algunas bombillas provoca
        un cambio raro a blanco mínimo.
        """
        if brightness <= 0:
            brightness = 1
        if brightness > 100:
            brightness = 100

        # Mapeo lineal 0–100 -> 10–255
        return max(10, min(255, int(10 + (245 * (brightness / 100)))))

    def set_brightness(self, brightness: int) -> None:
        """Ajusta el brillo manteniendo el último color RGB.

        Reglas:
        - Si brightness == 0 → se apaga la bombilla.
        - Si brightness > 0 → se ajusta el brillo usando PilotBuilder
          con el último color RGB para evitar que se ponga blanca.
        """
        ip = self._get_active_bulb()
        if not ip:
            return

        self.last_brightness = brightness

        async def do():
            bulb = wizlight(ip)

            if brightness <= 0:
                await bulb.turn_off()
                logging.info("Brillo 0% → bombilla APAGADA")
                return

            val = self._brightness_to_wiz(brightness)

            await bulb.turn_on(PilotBuilder(brightness=val, rgb=self.last_rgb))
            logging.info(f"Brillo ajustado a {brightness}% (valor WiZ={val})")

        self._run_async(do())

    def set_temperature(self, kelvin: int) -> None:
        """Ajusta la temperatura de color en modo blanco (colortemp)."""
        ip = self._get_active_bulb()
        if not ip:
            return

        # Rango típico de WiZ
        k = max(2200, min(6500, kelvin))

        async def do():
            await wizlight(ip).turn_on(PilotBuilder(colortemp=k))

        self._run_async(do())
        logging.info(f"Temperatura ajustada a {k}K")

    def activate_scene(self, scene_id: int) -> None:
        """Activa una escena predefinida de WiZ."""
        ip = self._get_active_bulb()
        if not ip:
            return

        async def do():
            await wizlight(ip).turn_on(PilotBuilder(scene=scene_id))

        self._run_async(do())
        logging.info(f"Escena activada: {scene_id}")
