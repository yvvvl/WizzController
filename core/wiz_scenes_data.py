"""
Mapeo de Escenas Nativas de WiZ a sus IDs.
Referencia: Documentación WiZ Pro y pywizlight scenes.py

Estructura completa de cada escena con metadatos.
"""

from typing import Dict, List, Tuple, Optional, NamedTuple

class SceneInfo(NamedTuple):
    """Información completa de una escena WiZ."""
    name: str
    scene_id: int
    icon: str
    is_dynamic: bool
    default_speed: Optional[int]  # 10-200, None si es estática
    description: str

# Catálogo completo de escenas WiZ
SCENE_CATALOG: Dict[int, SceneInfo] = {
    # Escenas Estáticas (Blancas y Funcionales)
    6: SceneInfo("Acogedor", 6, "🛋️", False, None, "Luz cálida y acogedora"),
    11: SceneInfo("Blanco Cálido", 11, "☕", False, None, "Blanco cálido estándar"),
    12: SceneInfo("Luz de Día", 12, "☀️", False, None, "Luz blanca natural"),
    13: SceneInfo("Blanco Frío", 13, "❄️", False, None, "Blanco frío brillante"),
    14: SceneInfo("Luz Nocturna", 14, "🌙", False, None, "Luz tenue para la noche"),
    15: SceneInfo("Concentración", 15, "👓", False, None, "Luz para trabajar"),
    16: SceneInfo("Relax", 16, "🧘", False, None, "Luz relajante"),
    18: SceneInfo("TV Time", 18, "📺", False, None, "Luz para ver TV"),
    19: SceneInfo("Cultivo Plantas", 19, "🌱", False, None, "Luz para plantas"),
    34: SceneInfo("Blanco Puro", 34, "⚪", False, None, "Blanco neutro"),
    
    # Escenas Dinámicas - Naturaleza
    1: SceneInfo("Océano", 1, "🌊", True, 50, "Olas del océano - azules y verdes"),
    3: SceneInfo("Atardecer", 3, "🌅", True, 50, "Colores del atardecer - naranjas y rojos"),
    5: SceneInfo("Chimenea", 5, "🔥", True, 50, "Parpadeo de fuego - rojos y naranjas"),
    7: SceneInfo("Bosque", 7, "🌲", True, 50, "Verdes del bosque"),
    23: SceneInfo("Inmersión Profunda", 23, "🌿", True, 50, "Azules profundos del océano"),
    24: SceneInfo("Jungla", 24, "🦜", True, 50, "Verdes vibrantes de la jungla"),
    
    # Escenas Dinámicas - Estaciones
    20: SceneInfo("Primavera", 20, "🌸", True, 50, "Colores primaverales"),
    21: SceneInfo("Verano", 21, "🌻", True, 50, "Amarillos y colores cálidos"),
    22: SceneInfo("Otoño", 22, "🍂", True, 50, "Naranjas y marrones del otoño"),
    
    # Escenas Dinámicas - Festividades
    27: SceneInfo("Navidad", 27, "🎄", True, 100, "Rojo y verde alternados"),
    28: SceneInfo("Halloween", 28, "🎃", True, 80, "Naranja y morado"),
    33: SceneInfo("Diwali", 33, "🪔", True, 60, "Colores festivos de Diwali"),
    
    # Escenas Dinámicas - Ambiente
    2: SceneInfo("Romance", 2, "❤️", True, 50, "Rojos y rosas románticos"),
    4: SceneInfo("Fiesta", 4, "🎉", True, 200, "Colores rápidos y vibrantes"),
    8: SceneInfo("Colores Pastel", 8, "🎨", True, 50, "Transición de colores pastel"),
    9: SceneInfo("Despertar", 9, "⏰", True, 40, "Amanecer gradual"),
    10: SceneInfo("A Dormir", 10, "🛏️", True, 40, "Atardecer gradual"),
    17: SceneInfo("Colores Verdaderos", 17, "🌈", True, 60, "Ciclo de colores vibrantes"),
    25: SceneInfo("Mojito", 25, "🍹", True, 50, "Verdes refrescantes"),
    29: SceneInfo("Luz de Vela", 29, "🕯️", True, 50, "Parpadeo suave de vela"),
    30: SceneInfo("Dorado Blanco", 30, "✨", True, 50, "Blanco dorado brillante"),
    31: SceneInfo("Pulso", 31, "💓", True, 100, "Pulsación rítmica"),
    32: SceneInfo("Steampunk", 32, "⚙️", True, 50, "Ámbar y cobre"),
    35: SceneInfo("Alarma", 35, "🔔", True, 200, "Alerta roja parpadeante"),
}

# Estructura para la UI: Categoría -> Lista de IDs de escenas
SCENES_DATA: Dict[str, List[int]] = {
    "Blancos & Funcional": [11, 12, 13, 6, 16, 15, 18, 14, 19, 34],
    "Dinámico - Naturaleza": [1, 3, 5, 7, 23, 24],
    "Dinámico - Estaciones": [20, 21, 22],
    "Dinámico - Festividades": [27, 28, 33],
    "Dinámico - Ambiente": [2, 4, 8, 9, 10, 17, 25, 29, 30, 31, 32, 35],
}

def get_scene_info(scene_id: int) -> Optional[SceneInfo]:
    """Obtiene información de una escena por su ID."""
    return SCENE_CATALOG.get(scene_id)

def get_all_dynamic_scenes() -> List[SceneInfo]:
    """Retorna todas las escenas dinámicas."""
    return [scene for scene in SCENE_CATALOG.values() if scene.is_dynamic]

def get_all_static_scenes() -> List[SceneInfo]:
    """Retorna todas las escenas estáticas."""
    return [scene for scene in SCENE_CATALOG.values() if not scene.is_dynamic]