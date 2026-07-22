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
]
