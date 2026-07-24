from __future__ import annotations

from types import SimpleNamespace

import flet as ft
import pytest

from ui.components.favorites_panel import FavoritesPanel


class FakeWiz:
    def get_kelvin_range(self):
        return 2300, 6100

    def get_state(self):
        return {"dimming": 74}


def _walk(root: ft.Control):
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        marker = id(control)
        if marker in seen:
            continue
        seen.add(marker)
        yield control

        content = getattr(control, "content", None)
        if isinstance(content, ft.Control):
            stack.append(content)
        controls = getattr(control, "controls", None)
        if isinstance(controls, list):
            stack.extend(item for item in controls if isinstance(item, ft.Control))


def _keys(root: ft.Control) -> set[str]:
    return {
        control.key
        for control in _walk(root)
        if isinstance(getattr(control, "key", None), str)
    }


def _control(root: ft.Control, key: str) -> ft.Control:
    return next(
        (control for control in _walk(root) if getattr(control, "key", None) == key),
        None,
    ) or pytest.fail(f"Control not found: {key}")


def _select(session, mode: str) -> None:
    session.kind.value = mode
    assert callable(session.kind.on_select)
    session.kind.on_select(SimpleNamespace(control=session.kind))


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    import config.paths as app_paths

    monkeypatch.setattr(app_paths, "_INITIALIZED_DIRS", set())


@pytest.fixture
def panel() -> FavoritesPanel:
    return FavoritesPanel(FakeWiz())


def test_rgb_session_uses_color_studio_picker(panel: FavoritesPanel) -> None:
    session = panel._create_editor_session()

    keys = _keys(session.editor)
    assert "favorites-editor-rgb" in keys
    assert "favorites-rgb-picker" in keys
    assert "favorites-rgb-hex" in keys
    assert "favorites-rgb-hue-purity" in keys
    assert "favorites-white-kelvin" not in keys
    assert set(session.state) == {"type", "rgb", "rgb_exact", "hue", "purity"}


def test_white_session_has_kelvin_and_brightness_without_rgb(
    panel: FavoritesPanel,
) -> None:
    session = panel._create_editor_session()
    _select(session, "white")

    keys = _keys(session.editor)
    assert "favorites-editor-white" in keys
    assert "favorites-white-kelvin-slider" in keys
    assert "favorites-white-brightness-slider" in keys
    assert "favorites-rgb-picker" not in keys
    assert "favorites-rgb-hex" not in keys
    assert "favorites-rgb-hue-purity" not in keys
    assert set(session.state) == {"type", "kelvin", "brightness"}
    kelvin = _control(session.editor, "favorites-white-kelvin-slider")
    brightness = _control(session.editor, "favorites-white-brightness-slider")
    assert (kelvin.min, kelvin.max) == (2300, 6100)
    assert (brightness.min, brightness.max) == (0, 100)


def test_scene_session_has_scene_selector_without_rgb(panel: FavoritesPanel) -> None:
    session = panel._create_editor_session()
    _select(session, "scene")

    keys = _keys(session.editor)
    assert "favorites-editor-scene" in keys
    assert "favorites-scene-selector" in keys
    assert "favorites-scene-visual" in keys
    assert "favorites-rgb-picker" not in keys
    assert "favorites-rgb-hex" not in keys
    assert set(session.state) == {"type", "scene", "scene_source", "speed"}


def test_brightness_session_only_has_brightness_editor(
    panel: FavoritesPanel,
) -> None:
    session = panel._create_editor_session()
    _select(session, "brightness")

    keys = _keys(session.editor)
    assert "favorites-editor-brightness" in keys
    assert "favorites-brightness-slider" in keys
    assert "favorites-rgb-picker" not in keys
    assert "favorites-white-kelvin-slider" not in keys
    assert "favorites-scene-selector" not in keys
    assert set(session.state) == {"type", "brightness"}


def test_real_dropdown_callback_replaces_every_mode_tree(
    panel: FavoritesPanel,
) -> None:
    session = panel._create_editor_session()
    roots: list[ft.Control] = []

    for mode, expected, absent in (
        ("rgb", "favorites-rgb-picker", "favorites-white-kelvin-slider"),
        ("white", "favorites-white-kelvin-slider", "favorites-rgb-picker"),
        ("scene", "favorites-scene-selector", "favorites-white-kelvin-slider"),
        ("brightness", "favorites-brightness-slider", "favorites-scene-selector"),
        ("rgb", "favorites-rgb-picker", "favorites-brightness-slider"),
    ):
        _select(session, mode)
        root = session.editor.controls[0]
        assert all(root is not previous for previous in roots)
        roots.append(root)
        keys = _keys(session.editor)
        assert expected in keys
        assert absent not in keys
        assert session.editor.data == mode


def test_type_change_rebuilds_preview_icon_immediately(panel: FavoritesPanel) -> None:
    session = panel._create_editor_session()
    rgb_icon = session.preview.content
    assert session.preview.data == "rgb"

    _select(session, "white")
    white_icon = session.preview.content
    assert session.preview.data == "white"
    assert white_icon is not rgb_icon
    assert white_icon.icon == ft.Icons.LIGHT_MODE_ROUNDED

    _select(session, "scene")
    scene_icon = session.preview.content
    assert session.preview.data == "scene"
    assert scene_icon is not white_icon

    _select(session, "brightness")
    assert session.preview.data == "brightness"
    assert session.preview.content is not scene_icon
    assert session.preview.content.icon == ft.Icons.BRIGHTNESS_6_ROUNDED


def test_white_and_brightness_sliders_update_preview_text(
    panel: FavoritesPanel,
) -> None:
    session = panel._create_editor_session()
    _select(session, "white")
    kelvin = _control(session.editor, "favorites-white-kelvin-slider")
    white_brightness = _control(
        session.editor,
        "favorites-white-brightness-slider",
    )
    kelvin.value = 4100
    white_brightness.value = 65
    white_brightness.on_change(SimpleNamespace(control=white_brightness))
    assert "4100K" in session.summary.value
    assert "65%" in session.summary.value

    _select(session, "brightness")
    brightness = _control(session.editor, "favorites-brightness-slider")
    brightness.value = 35
    brightness.on_change(SimpleNamespace(control=brightness))
    assert session.state == {"type": "brightness", "brightness": 35}
    assert "35%" in session.summary.value


def test_scene_selection_rebuilds_speed_controls_when_capability_changes(
    panel: FavoritesPanel,
) -> None:
    session = panel._create_editor_session()
    _select(session, "scene")
    selector = _control(session.editor, "favorites-scene-selector")
    assert "favorites-scene-speed-section" not in _keys(session.editor)

    selector.value = "wiz:1"
    selector.on_select(SimpleNamespace(control=selector))

    assert session.state["scene"] == 1
    assert "favorites-scene-speed-section" in _keys(session.editor)
    assert session.preview.data == "scene"


def test_each_mode_keeps_the_existing_persistence_contract(
    panel: FavoritesPanel,
) -> None:
    session = panel._create_editor_session()
    kind, value, _icon = panel._favorite_payload(session.state)
    assert kind == "rgb"
    assert isinstance(value, str) and value.startswith("#")

    _select(session, "white")
    kind, value, _icon = panel._favorite_payload(session.state)
    assert (kind, value) == ("white", 4000)

    _select(session, "scene")
    kind, value, _icon = panel._favorite_payload(session.state)
    assert kind == "scene"
    assert value == {"sceneId": 18, "speed": 100}

    _select(session, "brightness")
    kind, value, _icon = panel._favorite_payload(session.state)
    assert (kind, value) == ("brightness", 80)


def test_standalone_panel_without_i18n_supports_real_type_callback() -> None:
    standalone = FavoritesPanel(FakeWiz())
    session = standalone._create_editor_session()

    for mode in ("white", "scene", "brightness", "rgb"):
        _select(session, mode)
        assert f"favorites-editor-{mode}" in _keys(session.editor)
