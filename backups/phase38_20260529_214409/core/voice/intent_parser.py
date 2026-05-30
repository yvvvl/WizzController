from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from config.custom_scenes_manager import CustomScenesManager
from config.favorites_manager import FavoritesManager
from config.voice_training_manager import VoiceTrainingManager
from core import wiz_scenes


@dataclass
class VoiceIntent:
    ok: bool
    action: dict[str, Any] | None
    confidence: float
    reason: str
    source: str = "builtin"
    training_id: str | None = None


# Paleta ampliada pensada para habla natural en español/chileno.
# No intenta ser perfecta científicamente: prioriza nombres que una persona sí diría.
COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "rojo": (255, 0, 0),
    "verde": (0, 255, 0),
    "azul": (0, 80, 255),
    "amarillo": (255, 210, 0),
    "naranja": (255, 110, 0),
    "naranjo": (255, 110, 0),
    "morado": (155, 0, 255),
    "violeta": (155, 0, 255),
    "purpura": (155, 0, 255),
    "lila": (190, 120, 255),
    "lavanda": (180, 145, 255),
    "magenta": (255, 0, 190),
    "fucsia": (255, 0, 150),
    "rosa": (255, 40, 150),
    "rosado": (255, 40, 150),
    "celeste": (0, 190, 255),
    "cian": (0, 255, 220),
    "calipso": (0, 220, 210),
    "turquesa": (0, 255, 190),
    "menta": (60, 255, 170),
    "verde menta": (60, 255, 170),
    "limon": (180, 255, 0),
    "verde limon": (180, 255, 0),
    "dorado": (255, 190, 0),
    "ambar": (255, 150, 0),
    "coral": (255, 80, 70),
    "salmon": (255, 120, 90),
    "cyan": (0, 255, 220),
    "blue": (0, 80, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "yellow": (255, 210, 0),
    "orange": (255, 110, 0),
    "purple": (155, 0, 255),
    "pink": (255, 40, 150),
    "cyan": (0, 255, 220),
    "turquoise": (0, 255, 190),
    "gold": (255, 190, 0),
    "amber": (255, 150, 0),
}

# Variantes multi-palabra con prioridad antes del color base.
COLOR_ALIASES: list[tuple[str, tuple[int, int, int]]] = sorted(
    COLOR_MAP.items(), key=lambda item: len(item[0]), reverse=True
)


NUMBER_WORDS = {
    "cero": 0,
    "uno": 1,
    "un": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
    "cien": 100,
    "maximo": 100,
    "full": 100,
    "mitad": 50,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "one hundred": 100, "max": 100, "maximum": 100, "half": 50,
}

TENS_WORDS = {
    "veinti": 20,
    "treinta y": 30,
    "cuarenta y": 40,
    "cincuenta y": 50,
    "sesenta y": 60,
    "setenta y": 70,
    "ochenta y": 80,
    "noventa y": 90,
    "twenty ": 20,
    "thirty ": 30,
    "forty ": 40,
    "fifty ": 50,
    "sixty ": 60,
    "seventy ": 70,
    "eighty ": 80,
    "ninety ": 90,
}


ACTION_WORDS = (
    "pon", "poner", "pone", "deja", "dejar", "usa", "usar", "activa", "activar",
    "cambia", "cambiar", "modo", "luz", "ampolleta", "color", "brillo", "intensidad",
)


def normalize_text(text: str) -> str:
    text = str(text or "").lower().strip()
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )

    # Frases completas primero. Esto permite mezclar español/inglés sin cambiar
    # todo el motor a autodetección, que en clips cortos suele inventar idiomas.
    phrase_replacements = {
        "turn on": "prende",
        "switch on": "prende",
        "lights on": "prende luz",
        "light on": "prende luz",
        "turn off": "apaga",
        "switch off": "apaga",
        "shut off": "apaga",
        "lights off": "apaga luz",
        "light off": "apaga luz",
        "movie mode": "modo cine",
        "cinema mode": "modo cine",
        "tv mode": "modo tv",
        "warm white": "blanco calido",
        "cold white": "blanco frio",
        "cool white": "blanco frio",
        "neutral white": "blanco neutro",
        "full brightness": "brillo cien",
        "max brightness": "brillo cien",
        "half brightness": "brillo cincuenta",
        "all lights": "todas las luces",
        "the lights": "luz",
        "the light": "luz",
        "los luces": "la luz",
        "las luz": "la luz",
    }
    for old, new in phrase_replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)

    replacements = {
        "ampoyeta": "ampolleta",
        "ampolleta": "ampolleta",
        "amolleta": "ampolleta",
        "amoyeta": "ampolleta",
        "ampolletas": "ampolleta",
        "luca": "luz",
        "lucesita": "luz",
        "lucecita": "luz",
        "tele": "tv",
        "teli": "tv",
        "peli": "pelicula",
        "pelis": "peliculas",
        "calida": "calido",
        "fria": "frio",
        "prendela": "prende",
        "prendelo": "prende",
        "prendeme": "prende",
        "apagalo": "apaga",
        "apagala": "apaga",
        "apagame": "apaga",
        "subele": "sube",
        "bajale": "baja",
        "dejalo": "pon",
        "dejala": "pon",
        "ponle": "pon",
        "naranjo": "naranja",
        "purpura": "morado",
        "violeta": "morado",
        "cyan": "cian",
        "muisa": "wizz",
        "musa": "wizz",
        "miza": "wizz",
        "wisa": "wizz",
        "wis": "wiz",
        "whiz": "wiz",
        "weez": "wiz",
        "guis": "wiz",
        "guiz": "wiz",
        "light": "luz",
        "lights": "luz",
        "lamp": "luz",
        "bulb": "ampolleta",
        "bulbs": "ampolleta",
        "brightness": "brillo",
        "bright": "brillo",
        "intensity": "intensidad",
        "dim": "baja brillo",
        "brighter": "sube brillo",
        "dimmer": "baja brillo",
        "warm": "calido",
        "cold": "frio",
        "cool": "frio",
        "movie": "cine",
        "cinema": "cine",
        "scene": "escena",
        "mode": "modo",
        "set": "pon",
        "at": "al",
        "to": "al",
        "all": "todas",
    }
    for old, new in replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    text = re.sub(r"[^a-z0-9ñ% ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _contains_any(text: str, words: list[str] | tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def _word_number(text: str) -> int | None:
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            return int(value)

    # soporta: treinta y cinco, cuarenta y dos, veinticinco, etc.
    units = {k: v for k, v in NUMBER_WORDS.items() if 1 <= v <= 9}
    for prefix, base in TENS_WORDS.items():
        if prefix == "veinti":
            for unit, uvalue in units.items():
                if re.search(rf"\bveinti{unit}\b", text):
                    return base + uvalue
        else:
            for unit, uvalue in units.items():
                if re.search(rf"\b{re.escape(prefix)}\s+{unit}\b", text):
                    return base + uvalue
    return None


def _pct_from_text(text: str) -> int | None:
    m = re.search(r"(\d{1,3})\s*%?", text)
    if m:
        return max(0, min(100, int(m.group(1))))
    value = _word_number(text)
    if value is not None:
        return max(0, min(100, int(value)))
    return None


def _pct_near_brightness(text: str) -> int | None:
    """Busca porcentajes asociados a brillo/intensidad o frases tipo 'al 50'."""
    patterns = [
        r"(?:brillo|luminosidad|intensidad)\s*(?:al|a|en|de)?\s*(\d{1,3})\s*%?",
        r"(?:al|a|en|de)\s*(\d{1,3})\s*%?\s*(?:de\s*)?(?:brillo|luminosidad|intensidad)",
        r"(?:brillo|luminosidad|intensidad)\s*(?:al|a|en|de)?\s*([a-zñ ]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            pct = _pct_from_text(m.group(1))
            if pct is not None:
                return pct
    if re.search(r"\b(?:brillo|luminosidad|intensidad)\b", text):
        return _pct_from_text(text)
    return None


def _pct_after_connector(text: str) -> int | None:
    """Para frases naturales: 'prende la luz al 50', 'pon rojo al cien'."""
    m = re.search(r"\b(?:al|a|en|de)\s+(\d{1,3})\s*%?\b", text)
    if m:
        return max(0, min(100, int(m.group(1))))
    # 'al cincuenta', 'a la mitad'
    m = re.search(r"\b(?:al|a|en|de)\s+(?:la\s+)?([a-zñ ]{3,30})\b", text)
    if m:
        return _pct_from_text(m.group(1))
    return None


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _mix(rgb: tuple[int, int, int], target: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(_clamp_channel(c + (t - c) * amount) for c, t in zip(rgb, target))


def _scale(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(_clamp_channel(c * amount) for c in rgb)


def _apply_color_modifiers(text: str, rgb: tuple[int, int, int]) -> tuple[tuple[int, int, int], str]:
    label_bits: list[str] = []

    if _contains_any(text, ("pastel", "suave", "clarito", "clarita")):
        rgb = _mix(rgb, (255, 255, 255), 0.42)
        label_bits.append("suave")
    elif _contains_any(text, ("claro", "clara")):
        rgb = _mix(rgb, (255, 255, 255), 0.25)
        label_bits.append("claro")

    if _contains_any(text, ("oscuro", "oscura", "profundo", "profunda")):
        rgb = _scale(rgb, 0.45)
        label_bits.append("oscuro")

    if _contains_any(text, ("intenso", "intensa", "fuerte", "vivo", "viva", "saturado", "saturada")):
        # Mantiene el color base saturado. Solo marca etiqueta.
        label_bits.append("intenso")

    return rgb, " ".join(label_bits)


def _find_color_action(text: str) -> dict[str, Any] | None:
    if re.search(r"\bblanco\b", text):
        return None

    # 'color rgb 255 0 120' / 'rgb 255 0 120' para usuarios avanzados.
    m = re.search(r"\brgb\s+(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\b", text)
    if m:
        rgb = tuple(max(0, min(255, int(x))) for x in m.groups())
        return {"type": "rgb", "value": rgb, "name": f"RGB {rgb[0]} {rgb[1]} {rgb[2]}"}

    # 'hex ff00aa' si Whisper logra transcribirlo como texto.
    m = re.search(r"\b(?:hex|hexadecimal)\s*([a-f0-9]{6})\b", text)
    if m:
        hx = m.group(1)
        rgb = (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
        return {"type": "rgb", "value": rgb, "name": f"Color #{hx}"}

    for cname, rgb in COLOR_ALIASES:
        if re.search(rf"\b{re.escape(cname)}\b", text):
            rgb2, mod = _apply_color_modifiers(text, rgb)
            name = cname.capitalize() + (f" {mod}" if mod else "")
            return {"type": "rgb", "value": rgb2, "name": name}
    return None


def _find_scene_action(text: str) -> dict[str, Any] | None:
    # Alias frecuentes antes de fuzzy matching.
    if _contains_any(text, ("cine", "tv", "pelicula", "peliculas", "ver tv", "ver tele")):
        return {"type": "scene", "value": {"sceneId": 18, "speed": 100}, "name": "TV / Cine"}
    if _contains_any(text, ("fiesta", "carrete")):
        return {"type": "scene", "value": {"sceneId": 4, "speed": 160}, "name": "Fiesta"}
    if _contains_any(text, ("relax", "relajado", "relajar")):
        return {"type": "scene", "value": {"sceneId": 16, "speed": 100}, "name": "Relax"}
    return None


def _find_white_action(text: str) -> dict[str, Any] | None:
    if not ("blanco" in text or "temperatura" in text or "luz calido" in text or "luz frio" in text):
        return None
    if _contains_any(text, ("calido", "amarillo", "vela", "calentito")):
        return {"type": "white_percent", "value": 12, "name": "Blanco cálido"}
    if _contains_any(text, ("frio", "azulado", "helado")):
        return {"type": "white_percent", "value": 100, "name": "Blanco frío"}
    if _contains_any(text, ("neutro", "normal", "medio")):
        return {"type": "white_percent", "value": 50, "name": "Blanco neutro"}
    pct = _pct_from_text(text)
    if pct is not None:
        return {"type": "white_percent", "value": pct, "name": f"Blanco {pct}%"}
    return {"type": "white_percent", "value": 50, "name": "Blanco neutro"}


def _find_power_action(text: str) -> dict[str, Any] | None:
    # Evita que 'activa modo cine' se interprete como solo encender.
    has_mode = _contains_any(text, ("modo", "escena", "favorito"))
    if _contains_any(text, ("apaga", "apagar", "corta", "cortar")):
        return {"type": "method", "method": "turn_off", "name": "Apagar"}
    if _contains_any(text, ("enciende", "encender", "prende", "prender")):
        return {"type": "method", "method": "turn_on", "name": "Encender"}
    if not has_mode and _contains_any(text, ("activa la luz", "activar la luz")):
        return {"type": "method", "method": "turn_on", "name": "Encender"}
    if _contains_any(text, ("alterna", "alternar", "toggle", "cambia estado")):
        return {"type": "method", "method": "toggle", "name": "Alternar"}
    if _contains_any(text, ("restaura", "restaurar", "reset", "normal")) and not _contains_any(text, ("blanco normal", "luz normal")):
        return {"type": "method", "method": "reset_light", "name": "Restaurar"}
    return None


def _find_brightness_action(text: str, *, allow_connector: bool = False) -> dict[str, Any] | None:
    has_brightness_word = re.search(r"\b(?:brillo|luminosidad|intensidad)\b", text) is not None

    if has_brightness_word:
        if _contains_any(text, ("sube", "aumenta", "mas", "fuerte", "claro", "clarito")) and _pct_near_brightness(text) is None:
            return {"type": "brightness_delta", "value": 10, "name": "Subir brillo"}
        if _contains_any(text, ("baja", "disminuye", "menos", "suave", "bajito")) and _pct_near_brightness(text) is None:
            return {"type": "brightness_delta", "value": -10, "name": "Bajar brillo"}
        pct = _pct_near_brightness(text)
        if pct is not None:
            return {"type": "brightness", "value": max(10, pct), "name": f"Brillo {pct}%"}

    if allow_connector:
        pct = _pct_after_connector(text)
        if pct is not None:
            return {"type": "brightness", "value": max(10, pct), "name": f"Brillo {pct}%"}
    return None


def _dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action in actions:
        kind = str(action.get("type"))
        # Permitimos method + brightness + color, pero no dos colores o dos brillos.
        key = kind
        if kind == "method":
            key = f"method:{action.get('method')}"
        if key in seen and kind not in {"method"}:
            # Reemplaza la acción anterior del mismo tipo por la última mencionada.
            out = [a for a in out if str(a.get("type")) != kind]
        seen.add(key)
        out.append(action)
    return out


def _sequence_action(actions: list[dict[str, Any]]) -> dict[str, Any]:
    names = [str(a.get("name") or a.get("type")) for a in actions]
    return {"type": "sequence", "actions": actions, "name": " + ".join(names)}


class VoiceActionRegistry:
    """Lista y ejecución de acciones reutilizable por voz y UI de entrenamiento."""

    def __init__(self, wiz) -> None:
        self.wiz = wiz
        self.fav_manager = FavoritesManager()
        self.custom_manager = CustomScenesManager()

    def build_actions(self) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = [
            {"id": "general.toggle", "category": "General", "name": "Alternar encendido", "type": "method", "method": "toggle"},
            {"id": "general.on", "category": "General", "name": "Encender", "type": "method", "method": "turn_on"},
            {"id": "general.off", "category": "General", "name": "Apagar", "type": "method", "method": "turn_off"},
            {"id": "general.reset", "category": "General", "name": "Restaurar luz", "type": "method", "method": "reset_light"},
            {"id": "target.single", "category": "Destino", "name": "Modo una ampolleta", "type": "target_mode", "value": "single"},
            {"id": "target.all", "category": "Destino", "name": "Modo todas", "type": "target_mode", "value": "all"},
            {"id": "brightness.up", "category": "Brillo", "name": "Subir brillo 10%", "type": "brightness_delta", "value": 10},
            {"id": "brightness.down", "category": "Brillo", "name": "Bajar brillo 10%", "type": "brightness_delta", "value": -10},
        ]
        for pct in (10, 25, 50, 75, 100):
            actions.append({"id": f"brightness.{pct}", "category": "Brillo", "name": f"Brillo {pct}%", "type": "brightness", "value": pct})
        for name, rgb in COLOR_MAP.items():
            actions.append({"id": f"color.{name}", "category": "Color", "name": name.capitalize(), "type": "rgb", "value": rgb})
        for pct, label in ((0, "Blanco más cálido"), (25, "Blanco cálido"), (50, "Blanco neutro"), (75, "Blanco claro"), (100, "Blanco frío")):
            actions.append({"id": f"white.{pct}", "category": "Blancos", "name": label, "type": "white_percent", "value": pct})
        for sid, scene in wiz_scenes.CATALOG.items():
            actions.append({"id": f"scene.{sid}", "category": "Escenas WiZ", "name": scene.name, "type": "scene", "value": {"sceneId": sid, "speed": 100}})
        for fav in self.fav_manager.get_favorites():
            actions.append({"id": f"favorite.{fav.get('id')}", "category": "Favoritos", "name": fav.get("name", "Favorito"), "type": "favorite", "value": fav.get("id")})
        for scene in self.custom_manager.get_scenes():
            actions.append({"id": f"custom.{scene.get('id')}", "category": "Escenas personalizadas", "name": scene.get("name", "Escena"), "type": "custom_scene", "value": scene.get("id")})
        return actions

    def get_action(self, action_id: str) -> dict[str, Any] | None:
        for action in self.build_actions():
            if action.get("id") == action_id:
                return action
        return None

    def execute(self, action: dict[str, Any]) -> str:
        kind = action.get("type")
        if kind == "sequence":
            labels: list[str] = []
            for child in action.get("actions", []):
                if isinstance(child, dict):
                    labels.append(self.execute(child))
            return " + ".join(labels) if labels else "Secuencia vacía"
        if kind == "method":
            method = getattr(self.wiz, str(action.get("method")), None)
            if callable(method):
                method()
                return str(action.get("name") or action.get("method"))
        if kind == "target_mode":
            if hasattr(self.wiz, "set_control_mode"):
                self.wiz.set_control_mode(str(action.get("value") or "single"))
                return str(action.get("name") or "Cambiar destino")
        if kind == "brightness":
            self.wiz.set_brightness(int(action.get("value", 50)))
            return str(action.get("name") or "Brillo")
        if kind == "brightness_delta":
            st = self.wiz.get_state() if hasattr(self.wiz, "get_state") else {}
            current = int(st.get("dimming", 50) or 50)
            self.wiz.set_brightness(max(10, min(100, current + int(action.get("value", 0)))))
            return str(action.get("name") or "Brillo")
        if kind == "rgb":
            r, g, b = action.get("value", (255, 0, 0))
            self.wiz.set_rgb(int(r), int(g), int(b))
            return str(action.get("name") or "Color")
        if kind == "white_percent":
            pct = int(action.get("value", 50))
            if hasattr(self.wiz, "set_white_percent"):
                self.wiz.set_white_percent(pct)
            elif hasattr(self.wiz, "kelvin_from_percent"):
                self.wiz.set_white(self.wiz.kelvin_from_percent(pct))
            else:
                self.wiz.set_white(4000)
            return str(action.get("name") or "Blanco")
        if kind == "white_kelvin":
            self.wiz.set_white(int(action.get("value", 4000)))
            return str(action.get("name") or "Blanco")
        if kind == "scene":
            value = action.get("value") or {}
            if isinstance(value, dict):
                self.wiz.set_scene(int(value.get("sceneId", 18)), value.get("speed"))
            else:
                self.wiz.set_scene(int(value))
            return str(action.get("name") or "Escena")
        if kind == "favorite":
            fav = self.fav_manager.get_favorite(str(action.get("value")))
            if fav and hasattr(self.wiz, "apply_favorite"):
                self.wiz.apply_favorite(fav)
                return f"Favorito: {fav.get('name')}"
        if kind == "custom_scene":
            scene = self.custom_manager.get_scene(str(action.get("value")))
            if scene and hasattr(self.wiz, "apply_custom_scene"):
                self.wiz.apply_custom_scene(scene)
                return f"Escena personalizada: {scene.get('name')}"
        raise RuntimeError(f"Acción no soportada: {action}")


class VoiceIntentParser:
    def __init__(self, wiz) -> None:
        self.wiz = wiz
        self.training = VoiceTrainingManager()
        self.registry = VoiceActionRegistry(wiz)

    def parse(self, raw_text: str) -> VoiceIntent:
        text = normalize_text(raw_text)
        if not text:
            return VoiceIntent(False, None, 0.0, "No escuché texto")

        trained = self._parse_training(text)
        if trained.ok:
            return trained

        compound = self._parse_compound(text)
        if compound.ok:
            return compound

        named = self._parse_named_actions(text)
        if named.ok:
            return named

        return VoiceIntent(False, None, 0.0, f"No entendí: {raw_text}")

    def _parse_training(self, text: str) -> VoiceIntent:
        best_item = None
        best_score = 0.0
        for item in self.training.get_entries():
            phrase = normalize_text(item.get("phrase", ""))
            if not phrase:
                continue
            score = 1.0 if phrase == text else _ratio(phrase, text)
            if phrase in text or text in phrase:
                score = max(score, 0.86)
            if score > best_score:
                best_score = score
                best_item = item
        if best_item and best_score >= 0.80:
            return VoiceIntent(True, best_item.get("action"), best_score, "Frase entrenada", "training", best_item.get("id"))
        return VoiceIntent(False, None, best_score, "Sin frase entrenada")

    def _parse_compound(self, text: str) -> VoiceIntent:
        actions: list[dict[str, Any]] = []

        target = self._detect_target(text)
        if target:
            actions.append(target)

        power = _find_power_action(text)
        if power:
            actions.append(power)

        # Escena/blanco/color son modos de luz; normalmente solo uno debe ganar.
        mode_action = _find_scene_action(text)
        if not mode_action:
            mode_action = _find_white_action(text)
        if not mode_action:
            mode_action = _find_color_action(text)
        if mode_action:
            actions.append(mode_action)

        # Si ya hay encendido/color/escena/blanco, permitimos "al 50" aunque no diga brillo.
        allow_connector = bool(actions) and not (len(actions) == 1 and actions[0].get("type") == "target_mode")
        brightness = _find_brightness_action(text, allow_connector=allow_connector)
        if brightness:
            actions.append(brightness)

        actions = _dedupe_actions(actions)

        # Si no encontró nada y es un brillo simple, intenta delta/porcentaje sin secuencia.
        if not actions:
            brightness = _find_brightness_action(text, allow_connector=False)
            if brightness:
                actions.append(brightness)

        if not actions:
            return VoiceIntent(False, None, 0.0, "Sin builtin")

        if len(actions) == 1:
            action = actions[0]
            return VoiceIntent(True, action, 0.90, str(action.get("name") or action.get("type")))

        sequence = _sequence_action(actions)
        return VoiceIntent(True, sequence, 0.92, f"Secuencia: {sequence.get('name')}")

    def _detect_target(self, text: str) -> dict[str, Any] | None:
        if "modo una" in text or "solo una" in text or "una ampolleta" in text or "solo esta" in text:
            return {"type": "target_mode", "value": "single", "name": "Modo una ampolleta"}
        if "todas" in text or "todas las luces" in text or "todas las ampolletas" in text:
            return {"type": "target_mode", "value": "all", "name": "Modo todas"}
        return None

    # Compatibilidad: algunos módulos viejos podrían llamar _parse_builtin.
    def _parse_builtin(self, text: str) -> VoiceIntent:
        return self._parse_compound(text)

    def _parse_named_actions(self, text: str) -> VoiceIntent:
        actions = self.registry.build_actions()
        best = None
        best_score = 0.0
        for action in actions:
            name = normalize_text(action.get("name", ""))
            if not name:
                continue
            score = 0.0
            if name in text:
                score = 0.88
            else:
                score = _ratio(name, text)
                for token in ("modo", "escena", "favorito", "pon", "activa", "usa"):
                    score = max(score, _ratio(f"{token} {name}", text))
            if score > best_score:
                best_score = score
                best = action
        if best and best_score >= 0.70:
            return VoiceIntent(True, best, best_score, f"Acción por nombre: {best.get('name')}", "named")
        return VoiceIntent(False, None, best_score, "Sin acción por nombre")
