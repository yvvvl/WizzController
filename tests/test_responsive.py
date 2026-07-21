from types import SimpleNamespace

from ui.responsive import Viewport, clamp_size, dialog_dimensions, page_dimensions, quantize, quantize_down, safe_number


def test_viewport_modes_follow_panel_breakpoints():
    assert Viewport(619, 700).mode == "compact"
    assert Viewport(620, 700).mode == "medium"
    assert Viewport(899, 700).mode == "medium"
    assert Viewport(900, 700).mode == "wide"


def test_quantize_and_clamp_are_stable_for_resize():
    assert quantize(301, 8) == 304
    assert quantize(299, 8) == 296
    assert quantize(10, 0) == 10
    assert quantize_down(301, 8) == 296
    assert quantize_down(299, 8) == 296
    assert quantize_down(10, 0) == 10
    assert clamp_size(100, 220, 360) == 220
    assert clamp_size(500, 220, 360) == 360
    assert clamp_size(300, 220, 360) == 300


def test_safe_number_rejects_missing_non_positive_and_invalid_values():
    assert safe_number(None, 720) == 720
    assert safe_number("bad", 720) == 720
    assert safe_number(0, 720) == 720
    assert safe_number(-10, 720) == 720
    assert safe_number("640", 720) == 640


def test_dialog_dimensions_never_overflow_current_page():
    control = SimpleNamespace(page=SimpleNamespace(width=720, height=540))
    assert page_dimensions(control) == (720.0, 540.0)
    width, height = dialog_dimensions(control, 800, 700)
    assert width == 648
    assert height == 408


def test_dialog_dimensions_keep_minimums_when_page_metrics_are_unavailable():
    control = SimpleNamespace(page=SimpleNamespace(width=None, height=None))
    width, height = dialog_dimensions(control, 320, 300)
    assert width == 320
    assert height == 300
