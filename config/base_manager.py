import json
import os
import threading
import logging

class JsonManager:
    """
    Clase base para todos los gestores que usan JSON.
    Maneja la carga, guardado y acceso seguro a los datos.
    """
    def __init__(self, filename, default_data=None):
        self.logger = logging.getLogger(__name__)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.json_dir = os.path.join(self.base_dir, "json")
        self.filepath = os.path.join(self.json_dir, filename)
        self.lock = threading.Lock()
        
        # Asegurar que el directorio existe
        os.makedirs(self.json_dir, exist_ok=True)
        
        # Cargar datos
        self.data = self._load_data(default_data)

    def _load_data(self, default_data):
        if not os.path.exists(self.filepath):
            return default_data if default_data is not None else {}
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default_data if default_data is not None else {}

    def save(self):
        with self.lock:
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Error guardando {self.filepath}: {e}")

    # MÃ©todo clave para que no falle .get() en los paneles
    def get(self, key, default=None):
        if isinstance(self.data, dict):
            return self.data.get(key, default)
        return default
