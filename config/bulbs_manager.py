import logging
from typing import Dict
from .base_manager import JsonManager


class BulbsManager(JsonManager):
    def __init__(self) -> None:
        super().__init__("bulbs.json")
        if isinstance(self.data, list):
            logging.warning("Formato lista detectado en bulbs.json. Migrando a diccionario...")
            recovered = {}
            for item in self.data:
                if isinstance(item, dict) and item.get("ip"):
                    recovered[item["ip"]] = item
            self.data = recovered
            self.save()
        if not isinstance(self.data, dict):
            self.data = {}
            self.save()

    def get_bulbs(self) -> Dict[str, dict]:
        return self.data

    def add_bulb(self, bulb: dict) -> None:
        new_ip = bulb.get("ip")
        new_mac = bulb.get("mac")
        if not new_ip:
            return

        existing_data = dict(self.data.get(new_ip, {})) if isinstance(self.data.get(new_ip), dict) else {}
        old_ip_entry = None

        if new_mac:
            for stored_ip, stored_data in list(self.data.items()):
                if not isinstance(stored_data, dict):
                    continue
                if stored_data.get("mac") == new_mac and stored_ip != new_ip:
                    old_ip_entry = stored_ip
                    existing_data = {**stored_data, **existing_data}
                    break

        if old_ip_entry:
            logging.info(f"Actualizando IP de {new_mac}: {old_ip_entry} -> {new_ip}")
            del self.data[old_ip_entry]

        # Mantiene nombre si ya existía.
        old_name = existing_data.get("name")
        existing_data.update({k: v for k, v in bulb.items() if v is not None})
        if old_name and not bulb.get("name"):
            existing_data["name"] = old_name

        self.data[new_ip] = existing_data
        self.save()

    def remove_bulb(self, ip: str) -> None:
        if ip in self.data:
            del self.data[ip]
            self.save()

    def set_bulb_name(self, ip: str, name: str) -> None:
        if ip in self.data:
            self.data[ip]["name"] = name
            self.save()

    def get_bulb_name(self, ip: str) -> str | None:
        entry = self.data.get(ip, {})
        return entry.get("name") if isinstance(entry, dict) else None
