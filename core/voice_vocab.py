"""
Vocabulario y definiciones para el reconocimiento de voz natural.
"""

# Mapa de colores (Nombre -> RGB)
COLOR_MAP = {
    # Básicos
    "rojo": (255, 0, 0),
    "roja": (255, 0, 0),
    "verde": (0, 255, 0),
    "azul": (0, 0, 255),
    "blanco": (255, 255, 255),
    "blanca": (255, 255, 255),
    "negro": (0, 0, 0), # Apagar técnicamente
    
    # Variaciones
    "amarillo": (255, 255, 0),
    "amarilla": (255, 255, 0),
    "naranja": (255, 165, 0),
    "anaranjado": (255, 165, 0),
    "violeta": (238, 130, 238),
    "morado": (128, 0, 128),
    "rosa": (255, 192, 203),
    "rosado": (255, 192, 203),
    "fucsia": (255, 0, 255),
    "magenta": (255, 0, 255),
    "cian": (0, 255, 255),
    "celeste": (0, 191, 255),
    "turquesa": (64, 224, 208),
    "lima": (0, 255, 0),
    "limón": (255, 250, 205),
    "oro": (255, 215, 0),
    "dorado": (255, 215, 0),
    "plata": (192, 192, 192),
    "plateado": (192, 192, 192),
    "gris": (128, 128, 128),
    "marrón": (165, 42, 42),
    "café": (165, 42, 42),
    "carmesí": (220, 20, 60),
    "coral": (255, 127, 80),
    "índigo": (75, 0, 130),
    "lavanda": (230, 230, 250),
    "salmón": (250, 128, 114),
    "beige": (245, 245, 220),
    "menta": (189, 252, 201),
}

# Palabras que indican intención de temperatura
TEMP_MAP = {
    "calido": 2700,
    "cálido": 2700,
    "cálida": 2700,
    "calida": 2700,
    "frío": 6500,
    "frio": 6500,
    "fría": 6500,
    "fria": 6500,
    "neutro": 4500,
    "neutra": 4500,
    "lectura": 4000,
    "relax": 2200,
    "concentración": 6000,
}

# Palabras clave para escenas (Mapear a IDs de WiZ)
SCENE_KEYWORDS = {
    "oceano": 1, "océano": 1,
    "romance": 2, "romantico": 2,
    "atardecer": 3, "puesta de sol": 3,
    "fiesta": 4, "party": 4,
    "chimenea": 5, "fuego": 5,
    "bosque": 9, "selva": 9,
    "pastel": 11,
    "despertar": 12,
    "dormir": 13, "noche": 13,
    "cine": 8, "pelicula": 8,
    "navidad": 20,
}