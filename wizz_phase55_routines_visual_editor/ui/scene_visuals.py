from __future__ import annotations

import flet as ft

# Iconos locales. Evita depender de internet/imágenes externas y mantiene la app offline.
_SCENE_ICONS: dict[int, str] = {
    1: "WAVES_ROUNDED",
    2: "FAVORITE_ROUNDED",
    3: "WB_TWILIGHT_ROUNDED",
    4: "CELEBRATION_ROUNDED",
    5: "LOCAL_FIRE_DEPARTMENT_ROUNDED",
    6: "CHAIR_ROUNDED",
    7: "FOREST_ROUNDED",
    8: "PALETTE_ROUNDED",
    9: "ALARM_ROUNDED",
    10: "BEDTIME_ROUNDED",
    11: "COFFEE_ROUNDED",
    12: "WB_SUNNY_ROUNDED",
    13: "AC_UNIT_ROUNDED",
    14: "NIGHTLIGHT_ROUNDED",
    15: "CENTER_FOCUS_STRONG_ROUNDED",
    16: "SELF_IMPROVEMENT_ROUNDED",
    17: "COLOR_LENS_ROUNDED",
    18: "MOVIE_ROUNDED",
    19: "YARD_ROUNDED",
    20: "SPA_ROUNDED",
    21: "LIGHT_MODE_ROUNDED",
    22: "PARK_ROUNDED",
    23: "SCUBA_DIVING_ROUNDED",
    24: "PETS_ROUNDED",
    25: "LOCAL_BAR_ROUNDED",
    26: "NIGHTLIFE_ROUNDED",
    27: "PARK_ROUNDED",
    28: "CRUELTY_FREE_ROUNDED",
    29: "LOCAL_FIRE_DEPARTMENT_ROUNDED",
    30: "AUTO_AWESOME_ROUNDED",
    31: "FAVORITE_ROUNDED",
    32: "SETTINGS_ROUNDED",
    33: "FLARE_ROUNDED",
}

_SCENE_COLORS: dict[int, str] = {
    1: "#0096ff", 2: "#ff4d7e", 3: "#ff8c00", 4: "#ff00aa", 5: "#ff4500", 6: "#ffb066",
    7: "#22aa44", 8: "#ffb3d9", 9: "#ffe08a", 10: "#5b3fa0", 11: "#ffcf9e", 12: "#ffffff",
    13: "#cfe8ff", 14: "#6b5d8a", 15: "#dfeeff", 16: "#7fd0ff", 17: "#9b59ff", 18: "#8b5cf6",
    19: "#4caf50", 20: "#ff9ecb", 21: "#ffcf3a", 22: "#d2691e", 23: "#0066cc", 24: "#2ecc71",
    25: "#7fff66", 26: "#cc33ff", 27: "#ff2d2d", 28: "#ff7518", 29: "#ffb347", 30: "#ffd700",
    31: "#ff3366", 32: "#b08d57", 33: "#ff9933",
}


def scene_icon(scene_id: int, fallback=None):
    name = _SCENE_ICONS.get(int(scene_id), "AUTO_AWESOME_ROUNDED")
    return getattr(ft.Icons, name, fallback or ft.Icons.AUTO_AWESOME_ROUNDED)


def scene_color(scene_id: int, fallback: str = "#8b5cf6") -> str:
    return _SCENE_COLORS.get(int(scene_id), fallback)
