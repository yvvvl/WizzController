from __future__ import annotations

import flet as ft
import pytest

from ui.color_studio import hue_purity_to_rgb, rgb_to_hsv
from ui.components.color_panel import ColorPanel


class FakeWiz:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def get_kelvin_range(self):
        return 2200, 6500

    def set_rgb(self, r, g, b):
        self.calls.append(("rgb", r, g, b))

    def set_white(self, kelvin):
        self.calls.append(("white", kelvin))

    def set_brightness(self, value):
        self.calls.append(("brightness", value))

    def get_state(self):
        return {}


@pytest.fixture()
def panel(tmp_path, monkeypatch):
    monkeypatch.setenv("WIZZ_CONFIG_DIR", str(tmp_path))
    import config.paths as app_paths

    monkeypatch.setattr(app_paths, "_INITIALIZED_DIRS", set())
    return ColorPanel(FakeWiz())


def test_panel_builds_with_perceptual_horizontal_palette(panel: ColorPanel) -> None:
    assert panel._palette_geometry.image_width > panel._palette_geometry.image_height * 3
    assert panel._current_rgb() == (255, 0, 0)
    assert panel.color_section.visible is True
    assert panel.apply_row.visible is False
    assert "Pureza" in panel.palette_hs_label.value


def test_live_switch_controls_apply_button_visibility(panel: ColorPanel) -> None:
    panel.live_switch.value = False
    panel._live_changed()
    assert panel.apply_row.visible is True
    panel.live_switch.value = True
    panel._live_changed()
    assert panel.apply_row.visible is False


def test_manual_mode_does_not_send_until_apply(panel: ColorPanel) -> None:
    panel.live_switch.value = False
    panel._live_changed()
    panel._select_exact_rgb((0, 255, 0), source="test")
    assert panel.wiz.calls == []
    assert panel._pending is True

    original_execute_action = panel.executor.execute_action

    def execute_now(actions, threaded=True):
        for action in actions:
            original_execute_action(action)
        return "test"

    panel.executor.execute = execute_now
    panel._apply_current(manual=True)
    assert ("rgb", 0, 255, 0) in panel.wiz.calls
    assert ("brightness", panel.dimming) in panel.wiz.calls


def test_palette_mid_red_uses_perceptual_light_red(panel: ColorPanel) -> None:
    panel.hue = 0
    panel.purity = 0.5
    panel._exact_rgb = None
    assert panel._current_rgb() == hue_purity_to_rgb(0, 0.5) == (255, 148, 131)
    # It is not the magenta-pink HSV midpoint #FF8080.
    assert panel._current_rgb() != (255, 128, 128)


def test_palette_thumb_is_fully_contained(panel: ColorPanel) -> None:
    geo = panel._palette_geometry
    for hue, purity in ((0, 0), (360, 0), (0, 1), (360, 1)):
        left, top = geo.hue_purity_to_thumb_left_top(hue, purity)
        assert 0 <= left <= geo.outer_width - geo.thumb_diameter
        assert 0 <= top <= geo.outer_height - geo.thumb_diameter


def test_cct_thumb_is_fully_contained_in_bar(panel: ColorPanel) -> None:
    geo = panel._cct_geometry
    panel.temp_kelvin = panel._kelvin_min
    panel._refresh_cct()
    assert panel.cct_thumb.left == 0
    panel.temp_kelvin = panel._kelvin_max
    panel._refresh_cct()
    assert panel.cct_thumb.left == geo.outer_width - geo.thumb_diameter
    assert panel.cct_thumb.left + geo.thumb_diameter <= panel.cct_stack.width


def test_palette_touch_discards_dimmed_precise_rgb(panel: ColorPanel) -> None:
    panel._select_exact_rgb((128, 0, 0), source="precise")
    assert panel._exact_rgb == (128, 0, 0)
    geo = panel._palette_geometry
    panel._apply_palette_point(
        (geo.radius, geo.image_height - geo.radius),
        emit_live=False,
        interactive=False,
        update=False,
    )
    assert panel._exact_rgb is None
    assert panel._current_rgb() == (255, 0, 0)


def test_precise_hs_keeps_standard_hsv_semantics(panel: ColorPanel) -> None:
    panel.hex_field.value = panel._hex().upper()
    panel.r_field.value, panel.g_field.value, panel.b_field.value = map(str, panel._current_rgb())
    panel.h_field.value = "0"
    panel.s_field.value = "50"
    panel._on_precise_submit()
    assert panel._current_rgb() == (255, 128, 128)
    assert panel._exact_rgb == (255, 128, 128)
    _, saturation, _ = rgb_to_hsv(panel._current_rgb())
    assert saturation == pytest.approx(0.5, abs=1 / 255)


def test_external_rgb_sync_preserves_exact_value_without_emitting(panel: ColorPanel) -> None:
    panel.wiz.calls.clear()
    panel.sync_state({"r": 128, "g": 0, "b": 0, "dimming": 42})
    assert panel._current_rgb() == (128, 0, 0)
    assert panel.dimming == 42
    assert panel.wiz.calls == []


def test_external_kelvin_sync_changes_white_mode_without_emitting(panel: ColorPanel) -> None:
    panel.wiz.calls.clear()
    panel.sync_state({"temp": 2700, "dimming": 50})
    assert panel.mode == "white"
    assert panel.temp_kelvin == 2700
    assert panel.wiz.calls == []


def test_responsive_palette_uses_stable_buckets(panel: ColorPanel) -> None:
    panel.set_viewport(430, 600)
    assert (panel._palette_geometry.image_width, panel._palette_geometry.image_height) == (250, 82)
    first_src = panel.palette_image.src
    panel.set_viewport(440, 600)
    assert panel.palette_image.src is first_src
    panel.set_viewport(900, 700)
    assert (panel._palette_geometry.image_width, panel._palette_geometry.image_height) == (500, 152)


def test_palette_corner_mapping_on_panel(panel: ColorPanel) -> None:
    geo = panel._palette_geometry
    panel._apply_palette_point(
        (geo.radius, geo.radius),
        emit_live=False,
        interactive=False,
        update=False,
    )
    assert panel._current_rgb() == (255, 255, 255)
    panel._apply_palette_point(
        (geo.image_width - geo.radius, geo.image_height - geo.radius),
        emit_live=False,
        interactive=False,
        update=False,
    )
    assert panel._current_rgb() == (255, 0, 0)


def test_switching_rgb_white_mode_is_an_applyable_change(panel: ColorPanel) -> None:
    panel.live_switch.value = False
    panel._live_changed()
    panel._select_view("white")
    assert panel.mode == "white"
    assert panel._pending is True
    assert panel.apply_button.disabled is False


def test_manual_apply_builds_one_color_and_brightness_sequence(panel: ColorPanel) -> None:
    panel.live_switch.value = False
    panel._live_changed()
    panel._select_exact_rgb((255, 0, 0), source="test")
    captured: list[tuple[list[dict], bool]] = []

    def record(actions, threaded=True):
        captured.append((actions, threaded))
        return "test"

    panel.executor.execute = record
    panel._apply_current(manual=True)
    assert captured == [
        (
            [
                {"type": "rgb", "value": "#ff0000"},
                {"type": "brightness", "value": panel.dimming},
            ],
            True,
        )
    ]


def test_live_palette_is_throttled_but_final_value_is_forced(panel: ColorPanel) -> None:
    panel.wiz.calls.clear()
    panel._color_gate.interval = 60.0
    geo = panel._palette_geometry
    red = (geo.radius, geo.image_height - geo.radius)
    panel._apply_palette_point(red, emit_live=True, interactive=True, update=False)
    panel._apply_palette_point(red, emit_live=True, interactive=True, update=False)
    assert panel.wiz.calls.count(("rgb", 255, 0, 0)) == 1
    panel._finish_palette_edit()
    assert panel.wiz.calls.count(("rgb", 255, 0, 0)) == 2


def test_cct_sends_kelvin_not_preview_rgb(panel: ColorPanel) -> None:
    panel.wiz.calls.clear()
    panel._select_kelvin(2700, source="test")
    assert ("white", 2700) in panel.wiz.calls
    assert not any(call[0] == "rgb" for call in panel.wiz.calls)


@pytest.mark.parametrize("width", [360, 520, 720, 900, 1200, 1600])
def test_panel_reflows_across_supported_viewports(panel: ColorPanel, width: int) -> None:
    panel.set_viewport(width, 720)
    geo = panel._palette_geometry
    assert geo.image_width > 0
    assert geo.image_height > 0
    assert geo.outer_width == geo.image_width
    assert geo.outer_height == geo.image_height
    assert panel.palette_thumb.left is not None
    assert panel.cct_thumb.left is not None


def test_local_rgb_guard_blocks_delayed_external_state(panel: ColorPanel) -> None:
    panel._select_exact_rgb((255, 0, 0), source="local")
    panel.wiz.calls.clear()
    panel.sync_state({"r": 0, "g": 0, "b": 255})
    assert panel._current_rgb() == (255, 0, 0)
    assert panel.wiz.calls == []


def test_local_kelvin_guard_blocks_delayed_external_state(panel: ColorPanel) -> None:
    panel._select_kelvin(2700, source="local")
    panel.wiz.calls.clear()
    panel.sync_state({"temp": 6500})
    assert panel.temp_kelvin == 2700
    assert panel.wiz.calls == []


def _iter_control_tree(root):
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        marker = id(control)
        if marker in seen:
            continue
        seen.add(marker)
        yield control

        controls = getattr(control, "controls", None)
        if isinstance(controls, list):
            stack.extend(reversed(controls))

        for name in (
            "content",
            "leading",
            "trailing",
            "title",
            "subtitle",
            "label",
            "error_content",
        ):
            child = getattr(control, name, None)
            if isinstance(child, ft.Control):
                stack.append(child)


def test_wrapping_rows_never_host_expanded_children(panel: ColorPanel) -> None:
    offenders: list[str] = []
    for control in _iter_control_tree(panel):
        if not isinstance(control, ft.Row) or not bool(control.wrap):
            continue
        expanded = [
            child
            for child in control.controls
            if getattr(child, "expand", None) not in (None, False, 0)
        ]
        if expanded:
            offenders.append(
                f"Row(id={id(control)}) -> "
                + ", ".join(type(child).__name__ for child in expanded)
            )

    assert offenders == []


def test_runtime_headers_use_responsive_rows(panel: ColorPanel) -> None:
    assert isinstance(panel.header, ft.ResponsiveRow)
    assert isinstance(panel.palette_meta, ft.ResponsiveRow)
    assert isinstance(panel.favorite_header, ft.ResponsiveRow)
    assert isinstance(panel.apply_header, ft.ResponsiveRow)
