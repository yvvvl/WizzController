import asyncio
import logging
from pywizlight import discovery
from typing import List, Dict, Any

class BulbDiscovery:
    @staticmethod
    async def discover_bulbs(timeout: int = 3) -> list[dict]:
        """
        Descubre bombillas WiZ en la red local.
        Args:
            timeout (int): Tiempo de espera en segundos.
        Returns:
            list[dict]: Lista de bombillas encontradas con IP y MAC.
        """
        logging.info("Buscando bombillas WiZ en la red...")
        try:
            # Eliminar broadcast_space fijo para permitir detección automática en cualquier subred
            devices = await discovery.discover_lights(wait_time=timeout)
            bulbs = []
            for d in devices:
                try:
                    port = getattr(d, "port", 38899)
                except Exception:
                    port = 38899
                bulbs.append({"ip": d.ip, "mac": d.mac, "port": port})
            return bulbs
        except Exception as e:
            logging.error(f"Error descubriendo bombillas: {e}")
            return []

def discover_wiz_bulbs(timeout: int = 3) -> list[dict]:
    """
    Wrapper síncrono para descubrir bombillas WiZ.
    Args:
        timeout (int): Tiempo de espera en segundos.
    Returns:
        list[dict]: Lista de bombillas encontradas.
    """
    try:
        return asyncio.run(BulbDiscovery.discover_bulbs(timeout))
    except Exception as e:
        logging.error(f"Error en discover_wiz_bulbs: {e}")
        return []