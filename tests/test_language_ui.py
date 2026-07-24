from __future__ import annotations

from localization import (
    LANGUAGE_ENGLISH,
    LANGUAGE_SPANISH,
    LANGUAGE_SYSTEM,
    LocalizationManager,
    language_choice_keys,
    language_choices,
    translated_navigation,
)


def test_language_selector_exposes_system_and_manual_modes() -> None:
    assert language_choice_keys() == (
        LANGUAGE_SYSTEM,
        LANGUAGE_SPANISH,
        LANGUAGE_ENGLISH,
    )
    labels = dict(language_choices())
    assert "Windows" in labels[LANGUAGE_SYSTEM]
    assert labels[LANGUAGE_SPANISH] == "Español"
    assert labels[LANGUAGE_ENGLISH] == "English"


def test_navigation_changes_between_spanish_and_english() -> None:
    manager = LocalizationManager(
        preference="es",
        system_language_getter=lambda: "es",
    )
    assert translated_navigation(manager) == (
        "Inicio",
        "Color",
        "Escenas",
        "Favoritos",
        "Rutinas",
        "Ajustes",
        "Hotkeys",
    )

    manager.set_preference("en")
    assert translated_navigation(manager) == (
        "Home",
        "Color",
        "Scenes",
        "Favorites",
        "Routines",
        "Settings",
        "Hotkeys",
    )


def test_language_status_placeholders_are_valid() -> None:
    for language in ("en", "es"):
        manager = LocalizationManager(
            preference=language,
            system_language_getter=lambda: "en",
        )
        assert "{language}" not in manager.translate(
            "language.effective",
            language="English",
        )
        assert "{language}" not in manager.translate(
            "language.detected",
            language="English",
        )
