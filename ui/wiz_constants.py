import flet as ft

# Configuración de rendimiento
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
    {"id": 11, "name": "Cálido", "color": "#ffcc99", "icon": ft.Icons.LIGHT_MODE},
    {"id": 12, "name": "Luz Día", "color": "#ffffff", "icon": ft.Icons.WB_SUNNY},
    {"id": 13, "name": "Luz Fría", "color": "#ccffff", "icon": ft.Icons.AC_UNIT},
    {"id": 14, "name": "Luz Noche", "color": "#333333", "icon": ft.Icons.NIGHTLIGHT_ROUND},
]

# Escenas Dinámicas / Efectos
DYNAMIC_SCENES = [
    {"id": 1, "name": "Océano", "color": "#0099ff", "icon": ft.Icons.WATER_DROP},
    {"id": 2, "name": "Romance", "color": "#9933ff", "icon": ft.Icons.FAVORITE},
    {"id": 3, "name": "Atardecer", "color": "#ff6600", "icon": ft.Icons.WB_TWILIGHT},
    {"id": 4, "name": "Fiesta", "color": "#ff0066", "icon": ft.Icons.CELEBRATION},
    {"id": 5, "name": "Chimenea", "color": "#ff3300", "icon": ft.Icons.FIREPLACE},
    {"id": 6, "name": "Relax", "color": "#66ccff", "icon": ft.Icons.SPA},
    {"id": 7, "name": "Bosque", "color": "#00cc00", "icon": ft.Icons.FOREST},
    {"id": 8, "name": "Pastel", "color": "#ffccff", "icon": ft.Icons.PALETTE},
    {"id": 9, "name": "Despertar", "color": "#ffffcc", "icon": ft.Icons.ALARM},
    {"id": 10, "name": "Dormir", "color": "#330066", "icon": ft.Icons.BEDTIME},
    {"id": 27, "name": "Navidad", "color": "#ff0000", "icon": ft.Icons.CARD_GIFTCARD},
    {"id": 28, "name": "Halloween", "color": "#ff6600", "icon": ft.Icons.PEST_CONTROL_RODENT},
]

# Unimos ambas para búsquedas rápidas por ID
ALL_SCENES_MAP = {s["id"]: s for s in STATIC_SCENES + DYNAMIC_SCENES}