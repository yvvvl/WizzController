import logging
# Sin dependencias extrañas

ACTIONS_MAP = {
    "turn_on": "Encender Luz",
    "turn_off": "Apagar Luz",
    "set_brightness_max": "Brillo Máximo (100%)",
    "set_brightness_min": "Brillo Mínimo (10%)",
    "set_brightness_50": "Brillo Medio (50%)",
    "set_temp_warm": "Luz Cálida (2700K)",
    "set_temp_cold": "Luz Fría (6500K)",
    "set_temp_neutral": "Luz Neutra (4000K)",
    "set_color_red": "Poner color Rojo",
    "set_color_blue": "Poner color Azul",
    "set_color_green": "Poner color Verde",
    "set_color_custom": "Color Personalizado (Requiere valor)",
    "toggle_power": "Alternar Encendido/Apagado"
}

def get_all_actions() -> dict:
    return ACTIONS_MAP

def get_action_func(action_id: str):
    """
    Devuelve la función lambda correcta conectada al LightManager.
    """
    if action_id == "turn_on":
        return lambda lm: lm.turn_on()
        
    elif action_id == "turn_off":
        return lambda lm: lm.turn_off()
        
    elif action_id == "toggle_power":
        # ¡CORREGIDO! Ahora llama a toggle() en lugar de turn_on()
        return lambda lm: lm.toggle()
        
    elif action_id == "set_brightness_max":
        return lambda lm: lm.set_brightness(100)
    elif action_id == "set_brightness_min":
        return lambda lm: lm.set_brightness(10)
    elif action_id == "set_brightness_50":
        return lambda lm: lm.set_brightness(50)
        
    elif action_id == "set_temp_warm":
        return lambda lm: lm.set_temperature(2700)
    elif action_id == "set_temp_cold":
        return lambda lm: lm.set_temperature(6500)
    elif action_id == "set_temp_neutral":
        return lambda lm: lm.set_temperature(4000)
        
    elif action_id == "set_color_red":
        return lambda lm: lm.set_color((255, 0, 0))
    elif action_id == "set_color_blue":
        return lambda lm: lm.set_color((0, 0, 255))
    elif action_id == "set_color_green":
        return lambda lm: lm.set_color((0, 255, 0))
        
    elif action_id == "set_color_custom":
        return lambda lm, color: lm.set_color(color)

    else:
        logging.warning(f"Acción desconocida: {action_id}")
        return lambda lm: print(f"Acción {action_id} no implementada.")