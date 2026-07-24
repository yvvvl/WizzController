from __future__ import annotations

import flet as ft
import pytest

from config.custom_scenes_manager import CustomScenesManager
from config.favorites_manager import FavoritesManager
from config.hotkeys_manager import HotkeysManager
from config.routines_manager import RoutinesManager
from core.background.tray_service import TrayService
from localization import (
    LocalizationManager,
    translated_default_routine_description,
    translated_default_routine_name,
    translated_favorite_name,
    translated_scene_name,
)
from ui.components.hotkeys_panel import HotkeysPanel
from ui.components.routines_panel import RoutinesPanel
from ui.components.scenes_panel import ScenesPanel


class FakeWiz:
    def get_kelvin_range(self):
        return 2200, 6500

    def get_state(self):
        return {}


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


def test_remaining_primary_panels_render_english() -> None:
    i18n = LocalizationManager(preference="en")
    wiz = FakeWiz()
    hotkeys = HotkeysManager(wiz, auto_apply=False, i18n=i18n)

    scenes_text = _texts(ScenesPanel(wiz, i18n=i18n))
    routines_text = _texts(RoutinesPanel(wiz, i18n=i18n))
    hotkeys_text = _texts(HotkeysPanel(wiz, manager=hotkeys, i18n=i18n))

    assert "Scenes" in scenes_text
    assert "Ocean" in scenes_text
    assert "Routines" in routines_text
    assert "Study mode" in routines_text
    assert "Global hotkeys" in hotkeys_text
    assert "Toggle power" in hotkeys_text


def test_remaining_panels_update_after_language_change() -> None:
    i18n = LocalizationManager(preference="es")
    wiz = FakeWiz()
    hotkeys = HotkeysManager(wiz, auto_apply=False, i18n=i18n)
    panels = [
        ScenesPanel(wiz, i18n=i18n),
        RoutinesPanel(wiz, i18n=i18n),
        HotkeysPanel(wiz, manager=hotkeys, i18n=i18n),
    ]

    i18n.set_preference("en")
    for panel in panels:
        panel.set_language("en")

    assert "Scenes" in _texts(panels[0])
    assert "Routines" in _texts(panels[1])
    assert "Global hotkeys" in _texts(panels[2])
    assert hotkeys.action_label("toggle") == "Toggle power"


def test_user_created_names_are_not_translated() -> None:
    CustomScenesManager().add_scene(
        "Escena de Valentina",
        "rgb",
        {"r": 12, "g": 34, "b": 56, "dimming": 80},
    )
    RoutinesManager().add_routine(
        "Rutina de Valentina",
        [{"type": "turn_on"}],
        "Texto escrito por la usuaria",
    )
    i18n = LocalizationManager(preference="en")

    scenes_text = _texts(ScenesPanel(FakeWiz(), i18n=i18n))
    routines_text = _texts(RoutinesPanel(FakeWiz(), i18n=i18n))

    assert "Escena de Valentina" in scenes_text
    assert "Rutina de Valentina" in routines_text
    assert "Texto escrito por la usuaria" in routines_text


def test_built_in_content_uses_stable_ids() -> None:
    i18n = LocalizationManager(preference="en")
    night = RoutinesManager(i18n=i18n).get_routine("night")
    favorites = FavoritesManager()
    favorites.seed_defaults()
    red = next(favorite for favorite in favorites.get_favorites() if favorite.get("builtin") == "red")

    assert translated_scene_name(i18n, 18) == "TV / Cinema"
    assert translated_favorite_name(i18n, red) == "Red"
    assert translated_default_routine_name(i18n, night) == "Night mode"
    assert translated_default_routine_description(i18n, night) == (
        "Warm white and low brightness."
    )


def test_user_favorite_with_built_in_like_text_is_preserved() -> None:
    i18n = LocalizationManager(preference="en")
    custom = {"name": "Rojo", "type": "rgb", "value": "#ff0000"}

    assert translated_favorite_name(i18n, custom) == "Rojo"


def test_tray_status_and_target_are_localized() -> None:
    tray = TrayService.__new__(TrayService)
    tray.i18n = LocalizationManager(preference="en")
    tray._tray_status = lambda: {
        "online": True,
        "mode": "single",
        "ip": "192.168.1.20",
        "name": "Desk",
        "state": {"state": True, "dimming": 55},
    }

    assert tray._status_label() == "Desk: on · 55% · online"
    assert tray._target_label() == "Target: 1 light · 192.168.1.20"


def test_standalone_panels_keep_spanish_compatibility() -> None:
    wiz = FakeWiz()
    hotkeys = HotkeysManager(wiz, auto_apply=False)

    assert "Escenas" in _texts(ScenesPanel(wiz))
    assert "Rutinas" in _texts(RoutinesPanel(wiz))
    assert "Hotkeys globales" in _texts(HotkeysPanel(wiz, manager=hotkeys))
