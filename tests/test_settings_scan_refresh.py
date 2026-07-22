from __future__ import annotations

from types import SimpleNamespace

from ui.app import WizzApp
from ui.components.settings_panel import SettingsPanel


def _fake_app(*, selected_index: int, refresh_on_equal_state: bool):
    calls: list[tuple[int, dict]] = []
    panels = [SimpleNamespace(refresh_on_equal_state=False) for _ in range(7)]
    panels[selected_index].refresh_on_equal_state = refresh_on_equal_state
    app = SimpleNamespace(
        _last_state={"state": True, "dimming": 65},
        selected_index=selected_index,
        panels=panels,
        _sync_panel=lambda idx, state: calls.append((idx, dict(state))),
    )
    return app, calls


def test_settings_panel_opts_into_equal_state_refreshes() -> None:
    assert SettingsPanel.refresh_on_equal_state is True


def test_equal_light_state_still_refreshes_selected_settings_panel() -> None:
    app, calls = _fake_app(selected_index=5, refresh_on_equal_state=True)

    WizzApp.update_ui(app, {"state": True, "dimming": 65})

    assert calls == [(5, {"state": True, "dimming": 65})]


def test_equal_light_state_does_not_repaint_regular_panel() -> None:
    app, calls = _fake_app(selected_index=1, refresh_on_equal_state=False)

    WizzApp.update_ui(app, {"state": True, "dimming": 65})

    assert calls == []


def test_changed_light_state_keeps_normal_home_and_selected_refresh() -> None:
    app, calls = _fake_app(selected_index=5, refresh_on_equal_state=True)

    WizzApp.update_ui(app, {"state": False, "dimming": 65})

    assert {idx for idx, _state in calls} == {0, 5}
    assert app._last_state == {"state": False, "dimming": 65}
