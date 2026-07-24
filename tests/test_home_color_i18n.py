from __future__ import annotations

import flet as ft
import pytest

from localization import LocalizationManager
from ui.components.color_panel import ColorPanel
from ui.components.home_panel import HomePanel


class FakeWiz:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def get_kelvin_range(self):
        return 2200, 6500

    def get_state(self):
        return {}

    def refresh(self):
        self.calls.append(("refresh",))

    def turn_on(self):
        self.calls.append(("on",))

    def turn_off(self):
        self.calls.append(("off",))

    def set_brightness(self, value):
        self.calls.append(("brightness", value))

    def set_rgb(self, r, g, b):
        self.calls.append(("rgb", r, g, b))

    def set_white(self, kelvin):
        self.calls.append(("white", kelvin))

    def set_scene(self, scene_id, speed=None):
        self.calls.append(("scene", scene_id, speed))

    def reset_light(self):
        self.calls.append(("reset",))


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

        # Flet 0.85.2 buttons may keep their visible label as a plain string
        # in ``content`` instead of exposing a nested ft.Text control.
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


def test_home_panel_switches_between_spanish_and_english() -> None:
    manager = LocalizationManager(preference="es")
    panel = HomePanel(FakeWiz(), i18n=manager)
    assert "Inicio" in _texts(panel)
    assert "ACCESOS RÁPIDOS" in _texts(panel)

    manager.set_preference("en")
    panel.set_language("en")
    assert "Home" in _texts(panel)
    assert "QUICK ACTIONS" in _texts(panel)


def test_home_master_power_state_uses_active_language() -> None:
    manager = LocalizationManager(preference="en")
    panel = HomePanel(FakeWiz(), i18n=manager)

    panel._apply_power_visual(False)
    assert panel.master_label.value == "OFF"
    panel._apply_power_visual(True)
    assert panel.master_label.value == "ON"

    manager.set_preference("es")
    panel._apply_power_visual(False)
    assert panel.master_label.value == "APAGADO"


def test_color_panel_switches_between_spanish_and_english() -> None:
    manager = LocalizationManager(preference="es")
    panel = ColorPanel(FakeWiz(), i18n=manager)
    spanish = _texts(panel)
    assert "Guardar actual" in spanish
    assert "PALETA HUE / PUREZA" in spanish

    manager.set_preference("en")
    panel.set_language("en")
    english = _texts(panel)
    assert "Save current" in english
    assert "HUE / PURITY PALETTE" in english


def test_standalone_panels_keep_spanish_compatibility() -> None:
    home = HomePanel(FakeWiz())
    color = ColorPanel(FakeWiz())
    assert "Inicio" in _texts(home)
    assert "Guardar actual" in _texts(color)


def test_home_and_color_catalog_keys_exist_in_both_languages() -> None:
    for preference in ("es", "en"):
        manager = LocalizationManager(preference=preference)
        for key in (
            "home.header.title",
            "home.quick_section",
            "color_studio.save_current",
            "color_studio.palette_section",
            "color.name.red",
            "white.name.warm",
        ):
            assert manager.translate(key) != key
