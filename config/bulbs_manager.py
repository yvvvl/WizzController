import logging
from typing import Dict
from .base_manager import JsonManager

class BulbsManager(JsonManager):
    """
    Gestor de bombillas WiZ. 
    Deduplica por MAC Address y maneja la persistencia.
    """
    def __init__(self) -> None:
        super().__init__("bulbs.json")
        
        # --- Lógica de Migración ---
        # Si por alguna razón los datos cargados son una lista (formato antiguo),
        # los convertimos a diccionario y guardamos.
        if isinstance(self.data, list):
            logging.warning("Formato lista detectado en bulbs.json. Migrando a diccionario...")
            recovered = {}
            for item in self.data:
                if isinstance(item, dict) and item.get('ip'):
                    recovered[item['ip']] = item
            self.data = recovered
            self.save()

    def get_bulbs(self) -> Dict[str, dict]:
        return self.data

    def add_bulb(self, bulb: dict) -> None:
        """
        Agrega o actualiza una bombilla.
        Si la MAC ya existe en otra IP, borra la entrada antigua para evitar duplicados.
        """
        new_ip = bulb.get('ip')
        new_mac = bulb.get('mac')
        
        if not new_ip: return

        old_ip_entry = None
        existing_data = {}

        # Buscar si esta MAC ya existe registrada bajo OTRA IP
        # Usamos .copy() o list() porque self.data puede cambiar durante la iteración
        for stored_ip, stored_data in list(self.data.items()):
            if isinstance(stored_data, dict) and stored_data.get('mac') == new_mac:
                existing_data = stored_data
                if stored_ip != new_ip:
                    old_ip_entry = stored_ip
                break
        
        # Si detectamos mudanza de IP, borramos la vieja
        if old_ip_entry:
            logging.info(f"Actualizando IP de {new_mac}: {old_ip_entry} -> {new_ip}")
            del self.data[old_ip_entry]

        # Merge de datos (mantenemos nombre antiguo si existe)
        existing_data.update(bulb)
        
        # Guardamos en la nueva IP
        self.data[new_ip] = existing_data
        self.save()

    def set_bulb_name(self, ip: str, name: str) -> None:
        if ip in self.data:
            self.data[ip]["name"] = name
            self.save()

    def get_bulb_name(self, ip: str) -> str | None:
        return self.data.get(ip, {}).get("name")