from __future__ import annotations

import flet as ft
import pytest

from localization import LocalizationManager
from ui.components.favorites_panel import FavoritesPanel


class FakeWiz:
    def get_kelvin_range(self):
        return 2200, 6500


def _texts(root) -> list[str]:
    result: list[str] = []
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        marker = id(control)
        if marker in seen:
            continue
        seen.add(marker)

        value = getattr(control, "value", None)
        if isinstance(control, ft.Text) and isinstance(value, str):
            result.append(value)

        content = getattr(control, "content", None)
        if isinstance(content, str):
            result.append(content)
        elif isinstance(content, ft.Control):
            stack.append(content)

        controls = getattr(control, "controls", None)
        if isinstance(controls, list):
            stack.extend(controls)
        for name in ("title", "subtitle", "label", "leading", "trailing"):
            child = getattr(control, name, None)
            if isinstance(child, ft.Control):
                stack.append(child)
    return result


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    import config.paths as app_paths
    monkeypatch.setattr(app_paths, "_INITIALIZED_DIRS", set())


def test_favorites_panel_renders_spanish() -> None:
    manager = LocalizationManager(preference="es")
    panel = FavoritesPanel(FakeWiz(), i18n=manager)
    texts = _texts(panel)
    assert "Favoritos" in texts
    assert "Nuevo" in texts


def test_favorites_panel_renders_english() -> None:
    manager = LocalizationManager(preference="en")
    panel = FavoritesPanel(FakeWiz(), i18n=manager)
    texts = _texts(panel)
    assert "Favorites" in texts
    assert "New" in texts


def test_favorites_panel_without_i18n_keeps_spanish_compatibility() -> None:
    panel = FavoritesPanel(FakeWiz())
    assert "Favoritos" in _texts(panel)


def test_favorites_panel_updates_after_language_change() -> None:
    manager = LocalizationManager(preference="es")
    panel = FavoritesPanel(FakeWiz(), i18n=manager)

    manager.set_preference("en")
    panel.set_language("en")

    texts = _texts(panel)
    assert "Favorites" in texts
    assert "Saved colors, whites, scenes and brightness" in texts


def test_favorites_catalog_keys_exist_in_both_languages() -> None:
    keys = (
        "favorites.title",
        "favorites.subtitle",
        "favorites.new",
        "favorites.edit",
        "favorites.delete",
        "favorites.empty",
        "favorites.name",
        "favorites.type",
        "favorites.hex",
        "favorites.hue",
        "favorites.saturation",
        "favorites.lightness",
        "favorites.scene",
        "favorites.wiz_scene",
        "favorites.speed_value",
        "favorites.brightness_value",
        "favorites.scene_summary",
        "favorites.cancel",
        "favorites.save",
        "favorites.new_title",
        "favorites.edit_title",
        "favorites.default_name",
    )
    for preference in ("es", "en"):
        manager = LocalizationManager(preference=preference)
        for key in keys:
            assert manager.translate(key) != key
