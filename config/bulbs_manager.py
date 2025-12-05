import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

BULBS_PATH = os.path.join(os.path.dirname(__file__), 'json', 'bulbs.json')

class BulbsManager:
    """
    Gestor de bombillas WiZ. 
    CORREGIDO: Deduplicación por MAC Address. 
    Si una bombilla cambia de IP, actualiza la entrada existente en lugar de crear una nueva.
    """
    def __init__(self) -> None:
        self.file_path: str = BULBS_PATH
        ensure_json_file(self.file_path)
        self.bulbs: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            if os.path.getsize(self.file_path) == 0:
                return {}

            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
                # Corrección de formato (si era lista, pasarlo a dict)
                if isinstance(content, list):
                    logging.warning("Formato lista detectado. Migrando a diccionario...")
                    recovered = {}
                    for item in content:
                        if isinstance(item, dict) and item.get('ip'):
                            recovered[item['ip']] = item
                    return recovered
                
                return content
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
        Agrega o actualiza una bombilla.
        LÓGICA CLAVE: Busca por MAC. Si la bombilla ya existe en otra IP,
        borra la IP vieja y mueve los datos (nombre) a la nueva IP.
        """
        new_ip = bulb.get('ip')
        new_mac = bulb.get('mac')
        
        if not new_ip:
            return

        old_ip_entry = None
        existing_data = {}

        # 1. Buscar si esta MAC ya existe registrada bajo OTRA IP
        # Usamos list() para poder modificar el diccionario mientras iteramos si fuera necesario
        for stored_ip, stored_data in list(self.bulbs.items()):
            # Verificamos que stored_data sea un diccionario válido y coincida la MAC
            if isinstance(stored_data, dict) and stored_data.get('mac') == new_mac:
                existing_data = stored_data
                if stored_ip != new_ip:
                    old_ip_entry = stored_ip
                break
        
        # 2. Si detectamos que es la misma ampolleta con nueva IP
        if old_ip_entry:
            logging.info(f"Actualizando IP de {new_mac}: {old_ip_entry} -> {new_ip}")
            # BORRAMOS la entrada vieja para que no queden "fantasmas" (la .3)
            del self.bulbs[old_ip_entry]

        # 3. Merge de datos:
        # existing_data tiene el "name" antiguo.
        # bulb tiene la "ip" nueva.
        # .update() sobreescribe la IP vieja con la nueva, y mantiene el nombre.
        existing_data.update(bulb)
        
        # 4. Guardamos la entrada limpia en la nueva IP
        self.bulbs[new_ip] = existing_data
        self.save()

    def get_bulbs(self) -> Dict[str, dict]:
        return self.bulbs

    def set_bulb_name(self, ip: str, name: str) -> None:
        if ip in self.bulbs:
            self.bulbs[ip]["name"] = name
            self.save()

    def get_bulb_name(self, ip: str) -> str | None:
        return self.bulbs.get(ip, {}).get("name")