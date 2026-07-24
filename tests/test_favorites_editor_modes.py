from __future__ import annotations

import flet as ft
import pytest

from ui.components.favorites_panel import FavoritesPanel


class FakeWiz:
    def get_kelvin_range(self):
        return 2400, 6200

    def get_state(self):
        return {"dimming": 80}


def _keys(root: ft.Control) -> set[str]:
    result: set[str] = set()
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        marker = id(control)
        if marker in seen:
            continue
        seen.add(marker)

        key = getattr(control, "key", None)
        if isinstance(key, str):
            result.add(key)

        content = getattr(control, "content", None)
        if isinstance(content, ft.Control):
            stack.append(content)
        controls = getattr(control, "controls", None)
        if isinstance(controls, list):
            stack.extend(item for item in controls if isinstance(item, ft.Control))
    return result


def _control(root: ft.Control, key: str) -> ft.Control:
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        marker = id(control)
        if marker in seen:
            continue
        seen.add(marker)
        if getattr(control, "key", None) == key:
            return control
        content = getattr(control, "content", None)
        if isinstance(content, ft.Control):
            stack.append(content)
        controls = getattr(control, "controls", None)
        if isinstance(controls, list):
            stack.extend(item for item in controls if isinstance(item, ft.Control))
    raise AssertionError(f"Control not found: {key}")


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    import config.paths as app_paths

    monkeypatch.setattr(app_paths, "_INITIALIZED_DIRS", set())


@pytest.fixture
def panel() -> FavoritesPanel:
    return FavoritesPanel(FakeWiz())


def _render(panel: FavoritesPanel, mode: str) -> tuple[ft.Column, dict]:
    editor = ft.Column()
    state = panel._initial_editor_state()
    panel._render_editor_mode(editor, mode, state, lambda: None)
    return editor, state


def test_rgb_editor_contains_rgb_controls_but_not_kelvin(panel: FavoritesPanel) -> None:
    editor, _state = _render(panel, "rgb")

    keys = _keys(editor)
    assert "favorites-editor-rgb" in keys
    assert "favorites-rgb-picker" in keys
    assert "favorites-rgb-hex" in keys
    assert "favorites-rgb-hsv" in keys
    assert "favorites-white-kelvin" not in keys


def test_white_editor_contains_kelvin_and_brightness_but_not_rgb(
    panel: FavoritesPanel,
) -> None:
    editor, _state = _render(panel, "white")

    keys = _keys(editor)
    assert "favorites-editor-white" in keys
    assert "favorites-white-kelvin" in keys
    assert "favorites-white-kelvin-slider" in keys
    assert "favorites-white-brightness" in keys
    assert "favorites-white-brightness-slider" in keys
    assert "favorites-rgb-picker" not in keys
    assert "favorites-rgb-hex" not in keys


def test_scene_editor_contains_scene_selector_but_not_rgb(
    panel: FavoritesPanel,
) -> None:
    editor, _state = _render(panel, "scene")

    keys = _keys(editor)
    assert "favorites-editor-scene" in keys
    assert "favorites-scene-selector" in keys
    assert "favorites-scene-visual" in keys
    assert "favorites-rgb-picker" not in keys
    assert "favorites-rgb-hex" not in keys


def test_scene_speed_is_only_visible_for_dynamic_wiz_scenes(
    panel: FavoritesPanel,
) -> None:
    editor = ft.Column()
    state = panel._initial_editor_state(
        {"type": "scene", "value": {"sceneId": 18, "speed": 100}}
    )
    panel._render_editor_mode(editor, "scene", state, lambda: None)
    assert "favorites-scene-speed-section" not in _keys(editor)

    state["scene_source"] = "wiz:1"
    panel._render_editor_mode(editor, "scene", state, lambda: None)
    assert "favorites-scene-speed-section" in _keys(editor)


def test_custom_scene_is_listed_and_saved_as_a_compatible_favorite(
    panel: FavoritesPanel,
) -> None:
    custom = panel.custom_scenes.add_scene(
        "Desk white",
        "white",
        {"temp": 4200, "dimming": 75},
        "LIGHT_MODE",
    )
    editor, state = _render(panel, "scene")
    selector = _control(editor, "favorites-scene-selector")

    assert any(option.key == f"custom:{custom['id']}" for option in selector.options)
    state["scene_source"] = f"custom:{custom['id']}"
    assert panel._favorite_payload(state) == ("white", 4200, "LIGHT_MODE")


def test_brightness_editor_contains_only_brightness_controls(
    panel: FavoritesPanel,
) -> None:
    editor, _state = _render(panel, "brightness")

    keys = _keys(editor)
    assert "favorites-editor-brightness" in keys
    assert "favorites-brightness-value" in keys
    assert "favorites-brightness-slider" in keys
    assert "favorites-rgb-picker" not in keys
    assert "favorites-rgb-hex" not in keys
    assert "favorites-white-kelvin" not in keys
    assert "favorites-scene-selector" not in keys


def test_switch_rgb_to_white_replaces_the_complete_editor_tree(
    panel: FavoritesPanel,
) -> None:
    editor = ft.Column()
    state = panel._initial_editor_state()
    panel._render_editor_mode(editor, "rgb", state, lambda: None)
    rgb_root = editor.controls[0]

    panel._render_editor_mode(editor, "white", state, lambda: None)

    assert editor.data == "white"
    assert editor.controls[0] is not rgb_root
    assert "favorites-rgb-picker" not in _keys(editor)
    assert "favorites-white-kelvin" in _keys(editor)


def test_switch_white_to_scene_clears_white_visual_state(
    panel: FavoritesPanel,
) -> None:
    editor = ft.Column()
    state = panel._initial_editor_state()
    panel._render_editor_mode(editor, "white", state, lambda: None)
    white_root = editor.controls[0]

    panel._render_editor_mode(editor, "scene", state, lambda: None)

    assert editor.data == "scene"
    assert editor.controls[0] is not white_root
    assert "favorites-white-kelvin" not in _keys(editor)
    assert "favorites-scene-selector" in _keys(editor)


def test_standalone_panel_without_i18n_builds_all_editor_modes() -> None:
    standalone = FavoritesPanel(FakeWiz())

    for mode in ("rgb", "white", "scene", "brightness"):
        editor, _state = _render(standalone, mode)
        assert f"favorites-editor-{mode}" in _keys(editor)
