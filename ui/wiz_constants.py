import flet as ft

# ConfiguraciÃ³n de rendimiento
UPDATE_INTERVAL_SECONDS = 0.05

# Gradiente de 13 pasos
RICH_RAINBOW = [
    "#FF0000", "#FF7F00", "#FFFF00", "#7FFF00", 
    "#00FF00", "#00FF7F", "#00FFFF", "#007FFF", 
    "#0000FF", "#7F00FF", "#FF00FF", "#FF007F", "#FF0000"
]

# --- ESCENAS SEPARADAS ---

# Escenas de Blancos / Fijas
STATIC_SCENES = [
    {"id": 11, "name": "Cálido", "color": "#ffcc99", "icon": ft.icons.LIGHTBULB},
    {"id": 12, "name": "Luz DÃ­a", "color": "#ffffff", "icon": ft.icons.WB_SUNNY},
    {"id": 13, "name": "Luz FrÃ­a", "color": "#ccffff", "icon": ft.icons.AC_UNIT},
    {"id": 14, "name": "Luz Noche", "color": "#333333", "icon": ft.icons.NIGHTLIGHT_ROUND},
]

# Escenas DinÃ¡micas / Efectos
DYNAMIC_SCENES = [
    {"id": 1, "name": "OcÃ©ano", "color": "#0099ff", "icon": ft.icons.WATER_DROP},
    {"id": 2, "name": "Romance", "color": "#9933ff", "icon": ft.icons.FAVORITE},
    {"id": 3, "name": "Atardecer", "color": "#ff6600", "icon": ft.icons.WB_TWILIGHT},
    {"id": 4, "name": "Fiesta", "color": "#ff0066", "icon": ft.icons.CELEBRATION},
    {"id": 5, "name": "Chimenea", "color": "#ff3300", "icon": ft.icons.FIREPLACE},
    {"id": 6, "name": "Relax", "color": "#66ccff", "icon": ft.icons.SPA},
    {"id": 7, "name": "Bosque", "color": "#00cc00", "icon": ft.icons.FOREST},
    {"id": 8, "name": "Pastel", "color": "#ffccff", "icon": ft.icons.PALETTE},
    {"id": 9, "name": "Despertar", "color": "#ffffcc", "icon": ft.icons.ALARM},
    {"id": 10, "name": "Dormir", "color": "#330066", "icon": ft.icons.BEDTIME},
    {"id": 27, "name": "Navidad", "color": "#ff0000", "icon": ft.icons.CARD_GIFTCARD},
    {"id": 28, "name": "Halloween", "color": "#ff6600", "icon": ft.icons.PEST_CONTROL_RODENT},
]

# Unimos ambas para bÃºsquedas rÃ¡pidas por ID
ALL_SCENES_MAP = {s["id"]: s for s in STATIC_SCENES + DYNAMIC_SCENES}
