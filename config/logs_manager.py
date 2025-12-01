import os
import json
import logging
from typing import Dict, Any
from .config_manager import ensure_json_file

# Definimos la ruta de logs
LOGS_PATH = os.path.join(os.path.dirname(__file__), 'json', 'logs.json')

def setup_logging(level=logging.INFO):
    """
    Configura el sistema de logging global de la aplicación.
    Se llama desde main.py al inicio.
    """
    # Crear carpeta log si no existe
    log_dir = os.path.dirname(LOGS_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Mostrar en consola
            # Guardar en archivo wizz.log en la raíz o logs.json según prefieras. 
            # Usaremos un log de texto estándar para depuración:
            logging.FileHandler("wizz_debug.log", mode='a', encoding='utf-8')
        ]
    )

class LogsManager:
    """
    Gestor de logs de la app WiZ. Permite cargar, guardar y administrar logs.
    """
    def __init__(self) -> None:
        self.file_path: str = LOGS_PATH
        ensure_json_file(self.file_path)
        self.logs: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando logs: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando logs: {e}")

    def add_log(self, log: dict) -> None:
        """
        Agrega un log al registro.
        """
        key = log.get('timestamp')
        if key:
            self.logs[key] = log
            self.save()
        else:
            logging.warning("Intento de agregar log sin timestamp.")

    def get_logs(self) -> Dict[str, dict]:
        """
        Devuelve todos los logs registrados.
        """
        return self.logs