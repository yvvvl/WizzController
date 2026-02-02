"""
Mapeo de Escenas Nativas de WiZ a sus IDs.
Referencia: DocumentaciÃ³n WiZ Pro y pywizlight scenes.py

Estructura completa de cada escena con metadatos.
"""

from typing import Dict, List, Tuple, Optional, NamedTuple

class SceneInfo(NamedTuple):
    """InformaciÃ³n completa de una escena WiZ."""
    name: str
    scene_id: int
    icon: str
    is_dynamic: bool
    default_speed: Optional[int]  # 10-200, None si es estÃ¡tica
    description: str

# CatÃ¡logo completo de escenas WiZ
SCENE_CATALOG: Dict[int, SceneInfo] = {
    # Escenas EstÃ¡ticas (Blancas y Funcionales)
    6: SceneInfo("Acogedor", 6, "ï¸", False, None, "Luz cÃ¡lida y acogedora"),
    11: SceneInfo("Blanco CÃ¡lido", 11, "", False, None, "Blanco cÃ¡lido estÃ¡ndar"),
    12: SceneInfo("Luz de DÃ­a", 12, "ï¸", False, None, "Luz blanca natural"),
    13: SceneInfo("Blanco FrÃ­o", 13, "ï¸", False, None, "Blanco frÃ­o brillante"),
    14: SceneInfo("Luz Nocturna", 14, "", False, None, "Luz tenue para la noche"),
    15: SceneInfo("ConcentraciÃ³n", 15, "", False, None, "Luz para trabajar"),
    16: SceneInfo("Relax", 16, "", False, None, "Luz relajante"),
    18: SceneInfo("TV Time", 18, "", False, None, "Luz para ver TV"),
    19: SceneInfo("Cultivo Plantas", 19, "", False, None, "Luz para plantas"),
    34: SceneInfo("Blanco Puro", 34, "", False, None, "Blanco neutro"),
    
    # Escenas DinÃ¡micas - Naturaleza
    1: SceneInfo("OcÃ©ano", 1, "", True, 50, "Olas del ocÃ©ano - azules y verdes"),
    3: SceneInfo("Atardecer", 3, "", True, 50, "Colores del atardecer - naranjas y rojos"),
    5: SceneInfo("Chimenea", 5, "", True, 50, "Parpadeo de fuego - rojos y naranjas"),
    7: SceneInfo("Bosque", 7, "", True, 50, "Verdes del bosque"),
    23: SceneInfo("InmersiÃ³n Profunda", 23, "", True, 50, "Azules profundos del ocÃ©ano"),
    24: SceneInfo("Jungla", 24, "", True, 50, "Verdes vibrantes de la jungla"),
    
    # Escenas DinÃ¡micas - Estaciones
    20: SceneInfo("Primavera", 20, "", True, 50, "Colores primaverales"),
    21: SceneInfo("Verano", 21, "", True, 50, "Amarillos y colores cÃ¡lidos"),
    22: SceneInfo("OtoÃ±o", 22, "", True, 50, "Naranjas y marrones del otoÃ±o"),
    
    # Escenas DinÃ¡micas - Festividades
    27: SceneInfo("Navidad", 27, "", True, 100, "Rojo y verde alternados"),
    28: SceneInfo("Halloween", 28, "", True, 80, "Naranja y morado"),
    33: SceneInfo("Diwali", 33, "", True, 60, "Colores festivos de Diwali"),
    
    # Escenas DinÃ¡micas - Ambiente
    2: SceneInfo("Romance", 2, "â¤ï¸", True, 50, "Rojos y rosas romÃ¡nticos"),
    4: SceneInfo("Fiesta", 4, "", True, 200, "Colores rÃ¡pidos y vibrantes"),
    8: SceneInfo("Colores Pastel", 8, "", True, 50, "TransiciÃ³n de colores pastel"),
    9: SceneInfo("Despertar", 9, "â°", True, 40, "Amanecer gradual"),
    10: SceneInfo("A Dormir", 10, "ï¸", True, 40, "Atardecer gradual"),
    17: SceneInfo("Colores Verdaderos", 17, "", True, 60, "Ciclo de colores vibrantes"),
    25: SceneInfo("Mojito", 25, "", True, 50, "Verdes refrescantes"),
    29: SceneInfo("Luz de Vela", 29, "ï¸", True, 50, "Parpadeo suave de vela"),
    30: SceneInfo("Dorado Blanco", 30, "", True, 50, "Blanco dorado brillante"),
    31: SceneInfo("Pulso", 31, "", True, 100, "PulsaciÃ³n rÃ­tmica"),
    32: SceneInfo("Steampunk", 32, "ï¸", True, 50, "Ãmbar y cobre"),
    35: SceneInfo("Alarma", 35, "", True, 200, "Alerta roja parpadeante"),
}

# Estructura para la UI: CategorÃ­a -> Lista de IDs de escenas
SCENES_DATA: Dict[str, List[int]] = {
    "Blancos & Funcional": [11, 12, 13, 6, 16, 15, 18, 14, 19, 34],
    "DinÃ¡mico - Naturaleza": [1, 3, 5, 7, 23, 24],
    "DinÃ¡mico - Estaciones": [20, 21, 22],
    "DinÃ¡mico - Festividades": [27, 28, 33],
    "DinÃ¡mico - Ambiente": [2, 4, 8, 9, 10, 17, 25, 29, 30, 31, 32, 35],
}

def get_scene_info(scene_id: int) -> Optional[SceneInfo]:
    """Obtiene informaciÃ³n de una escena por su ID."""
    return SCENE_CATALOG.get(scene_id)

def get_all_dynamic_scenes() -> List[SceneInfo]:
    """Retorna todas las escenas dinÃ¡micas."""
    return [scene for scene in SCENE_CATALOG.values() if scene.is_dynamic]

def get_all_static_scenes() -> List[SceneInfo]:
    """Retorna todas las escenas estÃ¡ticas."""
    return [scene for scene in SCENE_CATALOG.values() if not scene.is_dynamic]
