from __future__ import annotations

from .manager import (
    DEFAULT_LANGUAGE,
    LANGUAGE_ENGLISH,
    LANGUAGE_SPANISH,
    LANGUAGE_SYSTEM,
    SUPPORTED_PREFERENCES,
    LocalizationManager,
    RuntimeLanguagePreference,
    configure_language,
    detect_system_language,
    format_fields,
    get_manager,
    normalize_language,
    tr,
    trn,
)
from .ui import (
    language_choice_keys,
    language_choices,
    native_language_name,
    translated_language_name,
    translated_navigation,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGE_ENGLISH",
    "LANGUAGE_SPANISH",
    "LANGUAGE_SYSTEM",
    "SUPPORTED_PREFERENCES",
    "LocalizationManager",
    "RuntimeLanguagePreference",
    "configure_language",
    "detect_system_language",
    "format_fields",
    "get_manager",
    "normalize_language",
    "tr",
    "trn",
    "language_choice_keys",
    "language_choices",
    "native_language_name",
    "translated_language_name",
    "translated_navigation",
]
