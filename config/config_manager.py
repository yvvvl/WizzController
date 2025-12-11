import os
import json
import logging
from typing import Dict, Any

# Definimos rutas base robustas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'json', 'config.json')

# --- FUNCIÓN RESTAURADA (Crucial para bulbs_manager) ---
def ensure_json_file(file_path: str, default_data: Any = None) -> None:
    """Asegura que exista un archivo JSON con datos por defecto."""
    if default_data is None:
        default_data = {}
    
    # Asegurar que el directorio exista
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Crear archivo si no existe o está vacío
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)

class ConfigManager:
    """
    Gestor de configuración unificado.
    Maneja configuración general y persistencia de la ventana.
    """
    def __init__(self, filepath=None):
        # Si no se pasa ruta, usamos la principal config.json
        self.file_path = filepath if filepath else CONFIG_PATH
        self.config = {}
        
        # Cargamos configuración asegurando que el archivo exista
        ensure_json_file(self.file_path, self._get_defaults())
        self._load()

    def _load(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error(f"Error cargando config: {e}")
            self.config = self._get_defaults()

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando config: {e}")

    def _get_defaults(self):
        """Define la estructura base del archivo de configuración."""
        return {
            "window": {
                "width": 900,
                "height": 800,
                "top": -1,
                "left": -1,
                "maximized": False
            }
        }

    # --- MÉTODOS GENÉRICOS (Para compatibilidad) ---
    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    # --- MÉTODOS DE PERSISTENCIA DE VENTANA (Nuevo) ---
    def get_window_geometry(self):
        return self.config.get("window", self._get_defaults()["window"])

    def set_window_geometry(self, width, height, top, left, maximized):
        # Validaciones de seguridad (evita guardar tamaños corruptos)
        if width < 400: width = 400
        if height < 500: height = 500
        
        self.config["window"] = {
            "width": int(width),
            "height": int(height),
            "top": int(top) if top is not None else -1,
            "left": int(left) if left is not None else -1,
            "maximized": bool(maximized)
        }
        self.save()