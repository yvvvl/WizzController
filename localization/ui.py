from __future__ import annotations

from collections.abc import Iterable

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
