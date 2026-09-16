"""Catálogo local de escenas WiZ (sceneId 1-33)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    id: int
    name: str
    glyph: str
    color: str
    dynamic: bool


CATALOG: dict[int, Scene] = {
    1: Scene(1, "Océano", "\ue706", "#0096ff", True),
    2: Scene(2, "Romance", "\ueb52", "#ff4d7e", True),
    3: Scene(3, "Atardecer", "\ue706", "#ff8c00", True),
    4: Scene(4, "Fiesta", "\ue7fc", "#ff00aa", True),
    5: Scene(5, "Chimenea", "\ue9a1", "#ff4500", True),
    6: Scene(6, "Acogedor", "\ue80f", "#ffb066", True),
    7: Scene(7, "Bosque", "\ue774", "#22aa44", True),
    8: Scene(8, "Pastel", "\ue790", "#ffb3d9", True),
    9: Scene(9, "Despertar", "\ue823", "#ffe08a", False),
    10: Scene(10, "Dormir", "\ue708", "#5b3fa0", False),
    11: Scene(11, "Blanco Cálido", "\ue706", "#ffcf9e", False),
    12: Scene(12, "Luz de Día", "\ue706", "#ffffff", False),
    13: Scene(13, "Blanco Frío", "\ue9ca", "#cfe8ff", False),
    14: Scene(14, "Luz Nocturna", "\ue708", "#6b5d8a", False),
    15: Scene(15, "Concentración", "\ue8b9", "#dfeeff", False),
    16: Scene(16, "Relax", "\ue8cb", "#7fd0ff", False),
    17: Scene(17, "Colores Reales", "\ue790", "#9b59ff", False),
    18: Scene(18, "TV / Cine", "\ue7f4", "#8b5cf6", False),
    19: Scene(19, "Plantas", "\ue774", "#4caf50", False),
    20: Scene(20, "Primavera", "\ue734", "#ff9ecb", True),
    21: Scene(21, "Verano", "\ue706", "#ffcf3a", True),
    22: Scene(22, "Otoño", "\ue774", "#d2691e", True),
    23: Scene(23, "Inmersión", "\ue7f4", "#0066cc", True),
    24: Scene(24, "Jungla", "\ue774", "#2ecc71", True),
    25: Scene(25, "Mojito", "\ue706", "#7fff66", True),
    26: Scene(26, "Club", "\ue7fc", "#cc33ff", True),
    27: Scene(27, "Navidad", "\ue734", "#ff2d2d", True),
    28: Scene(28, "Halloween", "\ue7f8", "#ff7518", True),
    29: Scene(29, "Vela", "\ue706", "#ffb347", True),
    30: Scene(30, "Dorado", "\ue735", "#ffd700", True),
    31: Scene(31, "Pulso", "\ueb52", "#ff3366", True),
    32: Scene(32, "Steampunk", "\ue713", "#b08d57", True),
    33: Scene(33, "Diwali", "\ue706", "#ff9933", True),
}

GROUPS: dict[str, list[int]] = {
    "Favoritas": [4, 1, 5, 18, 16, 27],
    "Naturaleza": [1, 3, 7, 23, 24, 25],
    "Ambiente": [2, 5, 6, 8, 17, 26, 29, 31, 32],
    "Blancos": [11, 12, 13, 14, 15, 16, 19, 30],
    "Rutinas": [9, 10],
    "Festividades": [27, 28, 33, 20, 21, 22],
}


def get(scene_id: int) -> Scene | None:
    return CATALOG.get(scene_id)
