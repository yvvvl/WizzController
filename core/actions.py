from typing import Callable, Dict, Any
import logging

action_registry: Dict[str, Callable] = {}

def register_action(action_id: str) -> Callable:
    """
    Decorador para registrar una acción en el sistema.
    Args:
        action_id (str): Identificador de la acción.
    Returns:
        Callable: Decorador que registra la función.
    """
    def decorator(func: Callable) -> Callable:
        action_registry[action_id] = func
        return func
    return decorator

def get_action(action_id: str) -> Callable:
    """
    Devuelve la función asociada a un action_id.
    Args:
        action_id (str): Identificador de la acción.
    Returns:
        Callable: Función asociada o lambda vacía.
    """
    actions = {
        "turn_on": lambda lm: safe_call(lm, "turn_on"),
        "turn_off": lambda lm: safe_call(lm, "turn_off"),
        "set_brightness": lambda lm, value=100: safe_call(lm, "set_brightness", value),
        "set_temperature": lambda lm, value=4000: safe_call(lm, "set_temperature", value),
        "set_color_custom": lambda lm, color: safe_call(lm, "set_color", color),
    }
    if action_id in actions:
        return actions[action_id]
    if action_id in action_registry:
        return action_registry[action_id]
    logging.warning(f"Acción desconocida: {action_id}")
    return lambda *args, **kwargs: None

def safe_call(obj: Any, method: str, *args, **kwargs) -> Any:
    """
    Llama de forma segura a un método de un objeto.
    Args:
        obj (Any): Objeto destino.
        method (str): Nombre del método.
        *args: Argumentos posicionales.
        **kwargs: Argumentos de palabra clave.
    Returns:
        Any: Resultado de la llamada o None si falla.
    """
    try:
        return getattr(obj, method)(*args, **kwargs)
    except Exception as e:
        logging.error(f"Error ejecutando acción {method}: {e}")
        return None

# Ejemplo de registro de acciones
@register_action("toggle_light")
def toggle_light(manager: Any) -> None:
    """
    Alterna el estado de la luz usando el manager.
    """
    if hasattr(manager, "toggle_light"):
        manager.toggle_light()

@register_action("turn_on")
def turn_on(manager: Any) -> None:
    """
    Enciende la luz usando el manager.
    """
    manager.turn_on()

@register_action("turn_off")
def turn_off(manager: Any) -> None:
    """
    Apaga la luz usando el manager.
    """
    manager.turn_off()

@register_action("brightness_increase")
def brightness_increase(manager: Any) -> None:
    """
    Aumenta el brillo usando el manager.
    """
    if hasattr(manager, "increase_brightness"):
        manager.increase_brightness()
    else:
        manager.set_brightness(100)
