from __future__ import annotations

from types import SimpleNamespace

from core.update_checker import ReleaseInfo
from localization import LocalizationManager
from ui.components.settings_panel import SettingsPanel


def _panel() -> SettingsPanel:
    panel = SettingsPanel.__new__(SettingsPanel)
    panel.i18n = LocalizationManager(preference="en")
    panel._update_check_in_progress = True
    panel._available_release = None
    panel.btn_check_updates = SimpleNamespace(disabled=True)
    panel.btn_open_release = SimpleNamespace(visible=False)
    panel.update_status = SimpleNamespace(value="", color="")
    return panel


def test_available_update_is_exposed_only_with_official_release_link():
    panel = _panel()
    release = ReleaseInfo(
        version="1.2.0",
        notes_url="https://github.com/yvvvl/WizzController/releases/tag/v1.2.0",
    )

    panel._apply_update_result(release)

    assert panel.btn_check_updates.disabled is False
    assert panel.btn_open_release.visible is True
    assert panel._available_release == release
    assert "1.2.0" in panel.update_status.value


def test_untrusted_release_link_is_not_exposed_to_the_user():
    panel = _panel()
    release = ReleaseInfo(version="1.2.0", notes_url="https://example.test/download")

    panel._apply_update_result(release)

    assert panel.btn_open_release.visible is False
    assert panel._available_release is None


def test_update_network_error_is_non_blocking_and_readable():
    panel = _panel()

    panel._apply_update_result(None, "unavailable")

    assert panel.btn_check_updates.disabled is False
    assert panel.btn_open_release.visible is False
    assert "unavailable" in panel.update_status.value.lower()


def test_updates_layout_uses_responsive_columns_not_expanded_wrapping_row():
    source = __import__("inspect").getsource(SettingsPanel._build)

    assert 'ft.ResponsiveRow(\n                        breakpoints=PANEL_BREAKPOINTS' in source
    assert 'vertical_alignment=ft.CrossAxisAlignment.CENTER,\n                        wrap=True,' not in source
