import logging
# Sin dependencias extrañas

# Catálogo amigable para usuarios: ID -> Descripción
ACTIONS_MAP = {
    # Encendido / Apagado
    "turn_on": "Encender Luz",
    "turn_off": "Apagar Luz",
    "toggle_power": "Alternar Encendido/Apagado",

    # Brillo rápidos
    "brightness_10": "Brillo 10%",
    "brightness_25": "Brillo 25%",
    "brightness_50": "Brillo 50%",
    "brightness_75": "Brillo 75%",
    "brightness_100": "Brillo 100%",
    "brightness_up_10": "Subir brillo +10%",
    "brightness_down_10": "Bajar brillo -10%",

    # Temperatura (Kelvin) rápidos
    "temp_2700": "Temperatura 2700K (cálida)",
    "temp_4000": "Temperatura 4000K (neutra)",
    "temp_6500": "Temperatura 6500K (fría)",
    "temp_up_300": "Subir temperatura +300K",
    "temp_down_300": "Bajar temperatura -300K",

    # Colores rápidos
    "color_red": "Color Rojo",
    "color_green": "Color Verde",
    "color_blue": "Color Azul",
    "color_yellow": "Color Amarillo",
    "color_cyan": "Color Cyan",
    "color_magenta": "Color Magenta",
    "color_white": "Color Blanco",
    "color_custom": "Color Personalizado (RGB)",

    # Escenas populares (WiZ)
    "scene_ocean": "Escena Océano",
    "scene_romance": "Escena Romance",
    "scene_sunset": "Escena Atardecer",
    "scene_party": "Escena Fiesta",
    "scene_fireplace": "Escena Chimenea",
    "scene_forest": "Escena Bosque",
    "scene_pastel": "Escena Colores Pastel",
    "scene_wakeup": "Escena Despertar",
    "scene_bedtime": "Escena A Dormir",
    "scene_christmas": "Escena Navidad",
    "scene_halloween": "Escena Halloween",
    "scene_candle": "Escena Luz de Vela",
    "scene_pulse": "Escena Pulso",
    "scene_steampunk": "Escena Steampunk",

    # Blancos / funcionales
    "scene_warm_white": "Blanco Cálido",
    "scene_daylight": "Luz de Día",
    "scene_cool_white": "Blanco Frío",
    "scene_night_light": "Luz Nocturna",
    "scene_relax": "Relax",
    "scene_focus": "Concentración",
    "scene_tv": "TV Time",

    # Misceláneos
    "refresh_state": "Actualizar estado (forzar)",
}

def get_all_actions() -> dict:
    """Devuelve el catálogo completo de acciones amigables para UI/voz."""
    return ACTIONS_MAP

def get_action_func(action_id: str):
    """Devuelve la función correcta conectada al LightManager.

    Nota: Para acciones que requieren argumentos (p.ej. color_custom), se devuelve
    una lambda con parámetros para que la UI/voz los pase.
    """
    # Encendido / Apagado
    if action_id == "turn_on":
        return lambda lm: lm.turn_on()
    if action_id == "turn_off":
        return lambda lm: lm.turn_off()
    if action_id == "toggle_power":
        return lambda lm: lm.toggle()

    # Brillo directos
    if action_id == "brightness_10":
        return lambda lm: lm.set_brightness(10)
    if action_id == "brightness_25":
        return lambda lm: lm.set_brightness(25)
    if action_id == "brightness_50":
        return lambda lm: lm.set_brightness(50)
    if action_id == "brightness_75":
        return lambda lm: lm.set_brightness(75)
    if action_id == "brightness_100":
        return lambda lm: lm.set_brightness(100)
    if action_id == "brightness_up_10":
        return lambda lm: lm.set_brightness(min(100, getattr(lm, 'last_brightness', 100) + 10))
    if action_id == "brightness_down_10":
        return lambda lm: lm.set_brightness(max(10, getattr(lm, 'last_brightness', 100) - 10))

    # Temperatura directos
    if action_id == "temp_2700":
        return lambda lm: lm.set_temperature(2700)
    if action_id == "temp_4000":
        return lambda lm: lm.set_temperature(4000)
    if action_id == "temp_6500":
        return lambda lm: lm.set_temperature(6500)
    if action_id == "temp_up_300":
        return lambda lm: lm.set_temperature(min(6500, (getattr(lm, 'last_temperature', 4000) + 300)))
    if action_id == "temp_down_300":
        return lambda lm: lm.set_temperature(max(2200, (getattr(lm, 'last_temperature', 4000) - 300)))

    # Colores rápidos
    if action_id == "color_red":
        return lambda lm: lm.set_color((255, 0, 0))
    if action_id == "color_green":
        return lambda lm: lm.set_color((0, 255, 0))
    if action_id == "color_blue":
        return lambda lm: lm.set_color((0, 0, 255))
    if action_id == "color_yellow":
        return lambda lm: lm.set_color((255, 255, 0))
    if action_id == "color_cyan":
        return lambda lm: lm.set_color((0, 255, 255))
    if action_id == "color_magenta":
        return lambda lm: lm.set_color((255, 0, 255))
    if action_id == "color_white":
        return lambda lm: lm.set_color((255, 255, 255))
    if action_id == "color_custom" or action_id == "set_color_custom":
        # Espera un parámetro (r,g,b) en 0-255
        return lambda lm, color: lm.set_color(color)

    # Escenas (IDs oficiales WiZ)
    if action_id == "scene_ocean":
        return lambda lm: lm.activate_scene(1, 50)
    if action_id == "scene_romance":
        return lambda lm: lm.activate_scene(2, 50)
    if action_id == "scene_sunset":
        return lambda lm: lm.activate_scene(3, 50)
    if action_id == "scene_party":
        return lambda lm: lm.activate_scene(4, 200)
    if action_id == "scene_fireplace":
        return lambda lm: lm.activate_scene(5, 50)
    if action_id == "scene_forest":
        return lambda lm: lm.activate_scene(7, 50)
    if action_id == "scene_pastel":
        return lambda lm: lm.activate_scene(8, 50)
    if action_id == "scene_wakeup":
        return lambda lm: lm.activate_scene(9, 40)
    if action_id == "scene_bedtime":
        return lambda lm: lm.activate_scene(10, 40)
    if action_id == "scene_christmas":
        return lambda lm: lm.activate_scene(27, 100)
    if action_id == "scene_halloween":
        return lambda lm: lm.activate_scene(28, 80)
    if action_id == "scene_candle":
        return lambda lm: lm.activate_scene(29, 50)
    if action_id == "scene_pulse":
        return lambda lm: lm.activate_scene(31, 100)
    if action_id == "scene_steampunk":
        return lambda lm: lm.activate_scene(32, 50)

    # Blancos / funcionales
    if action_id == "scene_warm_white":
        return lambda lm: lm.activate_scene(11)
    if action_id == "scene_daylight":
        return lambda lm: lm.activate_scene(12)
    if action_id == "scene_cool_white":
        return lambda lm: lm.activate_scene(13)
    if action_id == "scene_night_light":
        return lambda lm: lm.activate_scene(14)
    if action_id == "scene_relax":
        return lambda lm: lm.activate_scene(16)
    if action_id == "scene_focus":
        return lambda lm: lm.activate_scene(15)
    if action_id == "scene_tv":
        return lambda lm: lm.activate_scene(18)

    # Misceláneos
    if action_id == "refresh_state":
        return lambda lm: lm.get_state_sync()

    logging.warning(f"Acción desconocida: {action_id}")
    return lambda lm: print(f"Acción {action_id} no implementada.")