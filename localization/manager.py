from __future__ import annotations

import ctypes
import locale
import logging
import os
import threading
from collections.abc import Callable, Mapping
from string import Formatter
from typing import Any

from .catalogs import CATALOGS

_LOG = logging.getLogger(__name__)

LANGUAGE_SYSTEM = "system"
LANGUAGE_ENGLISH = "en"
LANGUAGE_SPANISH = "es"
SUPPORTED_PREFERENCES = (LANGUAGE_SYSTEM, LANGUAGE_ENGLISH, LANGUAGE_SPANISH)
DEFAULT_LANGUAGE = LANGUAGE_ENGLISH

LanguageListener = Callable[[str], None]


def normalize_language(value: Any, *, allow_system: bool = True) -> str:
    """Normalize locale/preference values to ``system``, ``en`` or ``es``."""

    text = str(value or "").strip().replace("_", "-").casefold()
    if allow_system and text in {"", "auto", "default", "system"}:
        return LANGUAGE_SYSTEM
    if text == "es" or text.startswith("es-"):
        return LANGUAGE_SPANISH
    if text == "en" or text.startswith("en-"):
        return LANGUAGE_ENGLISH
    return DEFAULT_LANGUAGE


def _windows_locale_name() -> str | None:
    if os.name != "nt":
        return None
    try:
        buffer = ctypes.create_unicode_buffer(85)
        result = ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
        return buffer.value if result else None
    except Exception:
        return None


def detect_system_language() -> str:
    """Detect Spanish Windows/OS locales; every other locale falls back to English."""

    candidates: list[str | None] = [
        _windows_locale_name(),
        os.environ.get("LC_ALL"),
        os.environ.get("LC_MESSAGES"),
        os.environ.get("LANG"),
    ]
    try:
        candidates.append(locale.getlocale()[0])
    except Exception:
        pass

    for candidate in candidates:
        if not candidate:
            continue
        normalized = normalize_language(candidate, allow_system=False)
        if normalized == LANGUAGE_SPANISH:
            return LANGUAGE_SPANISH
        if str(candidate).casefold().startswith("en"):
            return LANGUAGE_ENGLISH
    return DEFAULT_LANGUAGE


def format_fields(text: str) -> set[str]:
    fields: set[str] = set()
    for _literal, field_name, _format_spec, _conversion in Formatter().parse(text):
        if field_name:
            fields.add(field_name.split(".", 1)[0].split("[", 1)[0])
    return fields


class LocalizationManager:
    """Thread-safe localization state with runtime language changes."""

    def __init__(
        self,
        *,
        preference: str = LANGUAGE_SYSTEM,
        catalogs: Mapping[str, Mapping[str, str]] | None = None,
        system_language_getter: Callable[[], str] = detect_system_language,
    ) -> None:
        source = catalogs or CATALOGS
        self._catalogs = {
            str(language): dict(catalog)
            for language, catalog in source.items()
        }
        self._system_language_getter = system_language_getter
        self._lock = threading.RLock()
        self._listeners: list[LanguageListener] = []
        self._preference = normalize_language(preference)
        self._language = self._resolve(self._preference)

    @property
    def preference(self) -> str:
        with self._lock:
            return self._preference

    @property
    def language(self) -> str:
        with self._lock:
            return self._language

    def _resolve(self, preference: str) -> str:
        if preference == LANGUAGE_SYSTEM:
            detected = normalize_language(
                self._system_language_getter(),
                allow_system=False,
            )
            return detected if detected in self._catalogs else DEFAULT_LANGUAGE
        return preference if preference in self._catalogs else DEFAULT_LANGUAGE

    def set_preference(self, preference: str) -> bool:
        normalized = normalize_language(preference)
        with self._lock:
            next_language = self._resolve(normalized)
            changed = (
                normalized != self._preference
                or next_language != self._language
            )
            self._preference = normalized
            self._language = next_language
            listeners = tuple(self._listeners) if changed else ()

        for listener in listeners:
            try:
                listener(next_language)
            except Exception:
                _LOG.debug("Language listener failed", exc_info=True)
        return changed

    def refresh_system_language(self) -> bool:
        with self._lock:
            preference = self._preference
        if preference != LANGUAGE_SYSTEM:
            return False
        return self.set_preference(LANGUAGE_SYSTEM)

    def subscribe(self, listener: LanguageListener) -> Callable[[], None]:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def translate(self, key: str, /, **values: Any) -> str:
        with self._lock:
            language = self._language
            catalog = self._catalogs.get(language, {})
            fallback = self._catalogs.get(DEFAULT_LANGUAGE, {})
            text = catalog.get(key) or fallback.get(key) or key

        if not values:
            return text
        try:
            return text.format(**values)
        except (KeyError, IndexError, ValueError):
            _LOG.warning("Invalid localization placeholders for %s", key)
            return text

    def translate_count(self, key: str, count: int, /, **values: Any) -> str:
        suffix = "one" if int(count) == 1 else "other"
        values = {"count": int(count), **values}
        return self.translate(f"{key}.{suffix}", **values)

    def available_languages(self) -> tuple[str, ...]:
        return tuple(sorted(self._catalogs))


class RuntimeLanguagePreference:
    """Adapter for ``AppRuntimeManager`` without coupling the localization core."""

    KEY = "language"

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    def load(self) -> str:
        try:
            return normalize_language(self.runtime.get(self.KEY, LANGUAGE_SYSTEM))
        except Exception:
            return LANGUAGE_SYSTEM

    def save(self, preference: str) -> str:
        normalized = normalize_language(preference)
        try:
            self.runtime.update(**{self.KEY: normalized})
        except TypeError:
            self.runtime.update({self.KEY: normalized})
        return normalized


_manager = LocalizationManager()


def get_manager() -> LocalizationManager:
    return _manager


def configure_language(preference: str) -> bool:
    return _manager.set_preference(preference)


def tr(key: str, /, **values: Any) -> str:
    return _manager.translate(key, **values)


def trn(key: str, count: int, /, **values: Any) -> str:
    return _manager.translate_count(key, count, **values)
