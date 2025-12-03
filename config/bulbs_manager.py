import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

BULBS_PATH = os.path.join(os.path.dirname(__file__), 'json', 'bulbs.json')

class BulbsManager:
    """
    Gestor de bombillas WiZ. 
    Versión robusta: Maneja corrupción de datos y asegura formato de diccionario.
    """
    def __init__(self) -> None:
        self.file_path: str = BULBS_PATH
        ensure_json_file(self.file_path)
        self.bulbs: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            # Si el archivo está vacío, devolver dict vacío
            if os.path.getsize(self.file_path) == 0:
                return {}

            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
                # --- CORRECCIÓN DEL ERROR ---
                # Si el JSON es una lista (formato antiguo o erróneo), forzamos reinicio
                if isinstance(content, list):
                    logging.warning("bulbs.json tenía formato de lista. Reseteando a diccionario...")
                    return {}
                
                return content
        except json.JSONDecodeError:
            logging.warning("bulbs.json corrupto. Iniciando vacío.")
            return {}
        except Exception as e:
            logging.error(f"Error cargando bombillas: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.bulbs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando bombillas: {e}")

    def add_bulb(self, bulb: dict) -> None:
        """
        Agrega una bombilla al registro usando su IP como clave.
        """
        ip = bulb.get('ip')
        if ip:
            self.bulbs[ip] = bulb
            self.save()
        else:
            logging.warning("Intento de agregar bombilla sin IP.")

    def get_bulbs(self) -> Dict[str, dict]:
        """
        Devuelve todas las bombillas registradas.
        """
        return self.bulbs

    def set_bulb_name(self, ip: str, name: str) -> None:
        """Define un nombre amigable para una bombilla y guarda."""
        if not ip:
            return
        bulb = self.bulbs.get(ip, {"ip": ip})
        bulb["name"] = name
        self.bulbs[ip] = bulb
        self.save()

    def get_bulb_name(self, ip: str) -> str | None:
        try:
            return self.bulbs.get(ip, {}).get("name")
        except Exception:
            return None

# Test rápido
if __name__ == "__main__":
    manager = BulbsManager()
    print("Bombillas cargadas:", manager.get_bulbs())