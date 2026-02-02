import os
import json
import logging
from typing import Dict, Any

# Definimos rutas base robustas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'json', 'config.json')

# --- FUNCIN RESTAURADA (Crucial para bulbs_manager) ---
def ensure_json_file(file_path: str, default_data: Any = None) -> None:
    """Asegura que exista un archivo JSON con datos por defecto."""
    if default_data is None:
        default_data = {}
    
    # Asegurar que el directorio exista
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Crear archivo si no existe o estÃ¡ vacÃ­o
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)

class ConfigManager:
    """
    Gestor de configuraciÃ³n unificado.
    Maneja configuraciÃ³n general y persistencia de la ventana.
    """
    def __init__(self, filepath=None):
        # Si no se pasa ruta, usamos la principal config.json
        self.file_path = filepath if filepath else CONFIG_PATH
        self.config = {}
        
        # Cargamos configuraciÃ³n asegurando que el archivo exista
        ensure_json_file(self.file_path, self._get_defaults())
        self._load()

    def _load(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error(f"Error cargando config: {e}")
            self.config = self._get_defaults()

        # MigraciÃ³n suave: aÃ±ade claves nuevas sin romper configs viejas.
        try:
            defaults = self._get_defaults()

            def _merge(dst: dict, src: dict) -> bool:
                changed = False
                for k, v in src.items():
                    if k not in dst:
                        dst[k] = v
                        changed = True
                    elif isinstance(v, dict) and isinstance(dst.get(k), dict):
                        if _merge(dst[k], v):
                            changed = True
                return changed

            if isinstance(self.config, dict) and _merge(self.config, defaults):
                self.save()
        except Exception:
            logging.exception("No se pudo migrar config")

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error guardando config: {e}")

    def _get_defaults(self):
        """Define la estructura base del archivo de configuraciÃ³n."""
        return {
            "window": {
                "width": 900,
                "height": 800,
                "top": -1,
                "left": -1,
                "maximized": False
            },
            # Ajustes de performance/eco (pensado para ejecutar siempre liviano)
            "performance": {
                "eco_mode": True,
                # Perfiles: "balanced" (recomendado) o "ultra_light" (mÃ­nimo consumo, mÃ¡s latencia en cambios externos)
                "profile": "balanced",
                # Polling de estado (segundos)
                # Nota: state_poll_interval_s se mantiene por compatibilidad (actÃºa como MIN).
                "state_poll_interval_s": 2.5,
                "adaptive_polling_enabled": True,
                "state_poll_min_interval_s": 2.5,
                "state_poll_max_interval_s": 8.0,
                "state_poll_idle_after_s": 8.0,
                "state_poll_growth_factor": 1.4,
                # Backoff por IP offline
                "poll_backoff_base_s": 2.0,
                "poll_backoff_max_s": 30.0,
                # Worker de comandos (segundos)
                "command_active_sleep_s": 0.10,
                "command_idle_sleep_s": 0.35,
                # Monitor loop cuando no hay bombillas
                "monitor_no_bulbs_sleep_s": 3.0,
                # Discovery throttling
                "discovery_min_interval_s": 60.0,
                "discovery_backoff_max_s": 600.0
            },
            # Bandeja/segundo plano
            "tray": {
                "enabled": True
            }
        }

    # --- MTODOS GENRICOS (Para compatibilidad) ---
    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    # --- MTODOS DE PERSISTENCIA DE VENTANA (Nuevo) ---
    def get_window_geometry(self):
        return self.config.get("window", self._get_defaults()["window"])

    def get_performance(self) -> Dict[str, Any]:
        perf = self.config.get("performance")
        if not isinstance(perf, dict):
            perf = {}
        defaults = self._get_defaults().get("performance", {})
        merged = dict(defaults)
        merged.update(perf)
        return merged

    def get_tray(self) -> Dict[str, Any]:
        tray = self.config.get("tray")
        if not isinstance(tray, dict):
            tray = {}
        defaults = self._get_defaults().get("tray", {})
        merged = dict(defaults)
        merged.update(tray)
        return merged

    def set_performance_profile(self, profile: str) -> None:
        """Setea el perfil de performance (balanced/ultra_light) y guarda."""
        if "performance" not in self.config or not isinstance(self.config.get("performance"), dict):
            self.config["performance"] = {}
        self.config["performance"]["profile"] = str(profile)
        self.save()

    def set_window_geometry(self, width, height, top, left, maximized):
        # Validaciones de seguridad (evita guardar tamaÃ±os corruptos)
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
