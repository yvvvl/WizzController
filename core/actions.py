import logging
from typing import Callable, Any, Dict
from core.wiz_scenes_data import SCENES_DATA

# Registro maestro de acciones
AVAILABLE_ACTIONS: Dict[str, str] = {}
ACTION_CALLBACKS: Dict[str, Callable] = {}

def register(action_id: str, label: str, func: Callable):
    AVAILABLE_ACTIONS[action_id] = label
    ACTION_CALLBACKS[action_id] = func

def _safe_exec(manager: Any, method: str, *args, **kwargs):
    if hasattr(manager, method):
        try:
            getattr(manager, method)(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error ejecutando {method}: {e}")

# --- 1. COMANDOS BÁSICOS ---
register("turn_on", "Encender", lambda lm: _safe_exec(lm, "turn_on"))
register("turn_off", "Apagar", lambda lm: _safe_exec(lm, "turn_off"))
register("toggle", "Alternar (ON/OFF)", lambda lm: _safe_exec(lm, "toggle_light"))

# --- 2. BRILLO ---
register("brightness_up", "Brillo: Subir (+10%)", lambda lm: _safe_exec(lm, "set_brightness", getattr(lm, 'last_brightness', 50) + 10))
register("brightness_down", "Brillo: Bajar (-10%)", lambda lm: _safe_exec(lm, "set_brightness", getattr(lm, 'last_brightness', 50) - 10))
register("brightness_max", "Brillo: Máximo (100%)", lambda lm: _safe_exec(lm, "set_brightness", 100))
register("brightness_min", "Brillo: Mínimo (10%)", lambda lm: _safe_exec(lm, "set_brightness", 10))

# --- 3. TEMPERATURA ---
register("temp_warm", "Temp: Cálido (2700K)", lambda lm: _safe_exec(lm, "set_temperature", 2700))
register("temp_cold", "Temp: Frío (6500K)", lambda lm: _safe_exec(lm, "set_temperature", 6500))

# --- 4. COLOR PERSONALIZADO (Único) ---
# Eliminamos el bucle de colores fijos. Solo dejamos la opción dinámica.
AVAILABLE_ACTIONS["set_color_custom"] = "🎨 Color Personalizado (Selector)"

# --- 5. ESCENAS WiZ ---
for category, scenes_list in SCENES_DATA.items():
    for scene_name, scene_id, icon in scenes_list:
        aid = f"scene_{scene_id}"
        lbl = f"Escena: {icon} {scene_name}"
        register(aid, lbl, lambda lm, v=scene_id: _safe_exec(lm, "activate_scene", v))

# --- HELPERS ---
def get_action_label(action_id: str) -> str:
    return AVAILABLE_ACTIONS.get(action_id, action_id)

def get_action_func(action_id: str) -> Callable:
    if action_id == "set_color_custom":
        return lambda lm, color: _safe_exec(lm, "set_color", color)
    return ACTION_CALLBACKS.get(action_id, lambda lm: None)

def get_all_actions() -> Dict[str, str]:
    return dict(sorted(AVAILABLE_ACTIONS.items(), key=lambda item: item[1]))