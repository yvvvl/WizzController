from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Mapping

from .catalogs import CATALOGS
from .manager import (
    LANGUAGE_ENGLISH,
    LANGUAGE_SPANISH,
    LANGUAGE_SYSTEM,
    LocalizationManager,
    normalize_language,
)

# Labels intentionally remain bilingual/native so the user can always recover
# the selector even after choosing an unfamiliar interface language.
_LANGUAGE_CHOICES: tuple[tuple[str, str], ...] = (
    (LANGUAGE_SYSTEM, "Automático — Windows / Automatic — Windows"),
    (LANGUAGE_SPANISH, "Español"),
    (LANGUAGE_ENGLISH, "English"),
)


def language_choices() -> tuple[tuple[str, str], ...]:
    return _LANGUAGE_CHOICES


def language_choice_keys() -> tuple[str, ...]:
    return tuple(key for key, _label in _LANGUAGE_CHOICES)


def native_language_name(language: str) -> str:
    normalized = normalize_language(language, allow_system=False)
    return "Español" if normalized == LANGUAGE_SPANISH else "English"


def translated_language_name(manager: LocalizationManager, language: str) -> str:
    normalized = normalize_language(language, allow_system=False)
    key = "language.spanish" if normalized == LANGUAGE_SPANISH else "language.english"
    return manager.translate(key)


def translated_navigation(manager: LocalizationManager) -> tuple[str, ...]:
    return tuple(
        manager.translate(key)
        for key in (
            "nav.home",
            "nav.color",
            "nav.scenes",
            "nav.favorites",
            "nav.routines",
            "nav.settings",
            "nav.hotkeys",
        )
    )


_SCENE_GROUP_KEYS = {
    "favoritas": "scene.group.favorites",
    "favorites": "scene.group.favorites",
    "naturaleza": "scene.group.nature",
    "nature": "scene.group.nature",
    "ambiente": "scene.group.ambience",
    "ambience": "scene.group.ambience",
    "mood": "scene.group.ambience",
    "blancos": "scene.group.whites",
    "whites": "scene.group.whites",
    "rutinas": "scene.group.routines",
    "routines": "scene.group.routines",
    "festividades": "scene.group.holidays",
    "holidays": "scene.group.holidays",
}

_DEFAULT_ROUTINE_IDS = {
    "study",
    "night",
    "gaming",
    "cinema",
    "reading",
    "soft_off",
}

def translated_scene_name(
    manager: LocalizationManager,
    scene_id: int,
    fallback: str | None = None,
) -> str:
    key = f"scene.name.{int(scene_id)}"
    translated = manager.translate(key)
    return fallback if translated == key and fallback is not None else translated


def translated_scene_group(manager: LocalizationManager, group: str) -> str:
    raw = str(group or "")
    key = _SCENE_GROUP_KEYS.get(raw.casefold())
    return manager.translate(key) if key else raw


def translated_favorite_name(
    manager: LocalizationManager,
    favorite: Mapping[str, Any],
) -> str:
    raw = str(favorite.get("name") or "")
    builtin = str(favorite.get("builtin") or "")

    keys = {
        "red": "color.name.red",
        "blue": "color.name.blue",
        "warm": "white.name.warm",
        "neutral": "white.name.neutral",
        "cinema": "scene.name.18",
    }
    key = keys.get(builtin)
    return manager.translate(key) if key else raw


def _catalog_values(key: str) -> set[str]:
    return {
        str(catalog[key])
        for catalog in CATALOGS.values()
        if key in catalog
    }


def _translated_default_routine_field(
    manager: LocalizationManager,
    routine: Mapping[str, Any],
    field: str,
) -> str:
    routine_id = str(routine.get("id") or "")
    raw = str(routine.get(field) or "")
    if routine_id not in _DEFAULT_ROUTINE_IDS:
        return raw
    key = f"routine.default.{routine_id}.{field}"
    if not raw or raw in _catalog_values(key):
        return manager.translate(key)
    return raw


def translated_default_routine_name(
    manager: LocalizationManager,
    routine: Mapping[str, Any],
) -> str:
    return _translated_default_routine_field(manager, routine, "name")


def translated_default_routine_description(
    manager: LocalizationManager,
    routine: Mapping[str, Any],
) -> str:
    return _translated_default_routine_field(manager, routine, "description")
