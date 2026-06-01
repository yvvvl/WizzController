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
    1: Scene(1, "Océano", "🌊", "#0096ff", True),
    2: Scene(2, "Romance", "❤️", "#ff4d7e", True),
    3: Scene(3, "Atardecer", "🌅", "#ff8c00", True),
    4: Scene(4, "Fiesta", "🎉", "#ff00aa", True),
    5: Scene(5, "Chimenea", "🔥", "#ff4500", True),
    6: Scene(6, "Acogedor", "🛋️", "#ffb066", True),
    7: Scene(7, "Bosque", "🌲", "#22aa44", True),
    8: Scene(8, "Pastel", "🎨", "#ffb3d9", True),
    9: Scene(9, "Despertar", "⏰", "#ffe08a", False),
    10: Scene(10, "Dormir", "🛏️", "#5b3fa0", False),
    11: Scene(11, "Blanco Cálido", "☕", "#ffcf9e", False),
    12: Scene(12, "Luz de Día", "☀️", "#ffffff", False),
    13: Scene(13, "Blanco Frío", "❄️", "#cfe8ff", False),
    14: Scene(14, "Luz Nocturna", "🌙", "#6b5d8a", False),
    15: Scene(15, "Concentración", "🎯", "#dfeeff", False),
    16: Scene(16, "Relax", "🧘", "#7fd0ff", False),
    17: Scene(17, "Colores Reales", "🌈", "#9b59ff", False),
    18: Scene(18, "TV / Cine", "📺", "#8b5cf6", False),
    19: Scene(19, "Plantas", "🌱", "#4caf50", False),
    20: Scene(20, "Primavera", "🌸", "#ff9ecb", True),
    21: Scene(21, "Verano", "🌻", "#ffcf3a", True),
    22: Scene(22, "Otoño", "🍂", "#d2691e", True),
    23: Scene(23, "Inmersión", "🤿", "#0066cc", True),
    24: Scene(24, "Jungla", "🦜", "#2ecc71", True),
    25: Scene(25, "Mojito", "🍹", "#7fff66", True),
    26: Scene(26, "Club", "🪩", "#cc33ff", True),
    27: Scene(27, "Navidad", "🎄", "#ff2d2d", True),
    28: Scene(28, "Halloween", "🎃", "#ff7518", True),
    29: Scene(29, "Vela", "🕯️", "#ffb347", True),
    30: Scene(30, "Dorado", "✨", "#ffd700", True),
    31: Scene(31, "Pulso", "💓", "#ff3366", True),
    32: Scene(32, "Steampunk", "⚙️", "#b08d57", True),
    33: Scene(33, "Diwali", "🪔", "#ff9933", True),
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
