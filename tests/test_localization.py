from __future__ import annotations

from localization.catalogs import CATALOGS
from localization.manager import (
    LANGUAGE_SYSTEM,
    LocalizationManager,
    RuntimeLanguagePreference,
    format_fields,
    normalize_language,
)


def test_catalogs_have_identical_keys() -> None:
    languages = sorted(CATALOGS)
    baseline = set(CATALOGS[languages[0]])
    for language in languages[1:]:
        assert set(CATALOGS[language]) == baseline


def test_catalog_placeholders_match() -> None:
    keys = set(CATALOGS["en"])
    for key in keys:
        assert format_fields(CATALOGS["en"][key]) == format_fields(
            CATALOGS["es"][key]
        ), key


def test_system_preference_detects_spanish() -> None:
    manager = LocalizationManager(
        preference=LANGUAGE_SYSTEM,
        system_language_getter=lambda: "es-CL",
    )
    assert manager.preference == "system"
    assert manager.language == "es"
    assert manager.translate("nav.home") == "Inicio"


def test_unknown_system_language_falls_back_to_english() -> None:
    manager = LocalizationManager(
        preference=LANGUAGE_SYSTEM,
        system_language_getter=lambda: "de-DE",
    )
    assert manager.language == "en"
    assert manager.translate("nav.settings") == "Settings"


def test_runtime_language_change_notifies_once() -> None:
    manager = LocalizationManager(preference="en")
    events: list[str] = []
    manager.subscribe(events.append)

    assert manager.set_preference("es") is True
    assert manager.set_preference("es") is False
    assert events == ["es"]


def test_missing_translation_falls_back_to_key() -> None:
    manager = LocalizationManager(preference="en")
    assert manager.translate("missing.example") == "missing.example"


def test_pluralization_and_formatting() -> None:
    manager = LocalizationManager(preference="en")
    assert manager.translate_count("bulbs.search_done", 1) == (
        "Search complete · 1 light available."
    )
    assert manager.translate_count("bulbs.search_done", 2) == (
        "Search complete · 2 lights available."
    )


def test_normalize_language() -> None:
    assert normalize_language("es_CL") == "es"
    assert normalize_language("EN-us") == "en"
    assert normalize_language("auto") == "system"
    assert normalize_language("fr-FR", allow_system=False) == "en"


class FakeRuntime:
    def __init__(self) -> None:
        self.data = {"language": "es"}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def update(self, **values):
        self.data.update(values)


def test_runtime_preference_adapter() -> None:
    runtime = FakeRuntime()
    preference = RuntimeLanguagePreference(runtime)
    assert preference.load() == "es"
    assert preference.save("system") == "system"
    assert runtime.data["language"] == "system"
