from dataclasses import FrozenInstanceError, fields

import pytest

from core.platform.capabilities import (
    CapabilityState,
    CapabilityStatus,
    DesktopCapabilities,
)
from core.platform.contracts import (
    AutostartService,
    HotkeyService,
    SingleInstanceService,
    SystemIntegrationService,
    TrayBackend,
    WindowService,
)
from core.platform.fakes import (
    FakeAutostartService,
    FakeHotkeyService,
    FakeSingleInstanceService,
    FakeSystemIntegrationService,
    FakeTrayBackend,
    FakeWindowService,
)


CAPABILITY_NAMES = (
    "hotkey_registration",
    "hotkey_recording",
    "tray",
    "tray_default_action",
    "start_at_login",
    "window_show",
    "window_hide",
    "window_restore",
    "window_focus",
    "work_area_positioning",
    "frameless",
    "always_on_top",
    "taskbar_skip",
    "single_instance_exclusion",
    "single_instance_activation",
    "open_folder",
)


@pytest.mark.parametrize(
    ("factory_name", "expected_status", "usable"),
    [
        ("available", CapabilityStatus.AVAILABLE, True),
        ("unavailable", CapabilityStatus.UNAVAILABLE, False),
        ("degraded", CapabilityStatus.DEGRADED, True),
        (
            "permission_required",
            CapabilityStatus.PERMISSION_REQUIRED,
            False,
        ),
    ],
)
def test_capability_state_factories_preserve_status_reason_and_usability(
    factory_name,
    expected_status,
    usable,
):
    factory = getattr(CapabilityState, factory_name)

    state = factory("  desktop policy  ")

    assert state.status is expected_status
    assert state.reason == "desktop policy"
    assert state.is_usable is usable
    assert state.is_available is (
        expected_status is CapabilityStatus.AVAILABLE
    )


def test_capability_state_accepts_string_status_and_normalizes_blank_reason():
    state = CapabilityState("degraded", "  ")

    assert state.status is CapabilityStatus.DEGRADED
    assert state.reason is None


def test_capability_state_rejects_unknown_status_and_non_text_reason():
    with pytest.raises(ValueError):
        CapabilityState("unknown")
    with pytest.raises(TypeError, match="reason"):
        CapabilityState.available(123)


def test_capability_state_is_immutable():
    state = CapabilityState.available()

    with pytest.raises(FrozenInstanceError):
        state.reason = "changed"


def test_desktop_capabilities_defaults_every_capability_to_unavailable():
    capabilities = DesktopCapabilities()

    assert tuple(item.name for item in fields(capabilities)) == CAPABILITY_NAMES
    assert all(
        getattr(capabilities, name).status
        is CapabilityStatus.UNAVAILABLE
        for name in CAPABILITY_NAMES
    )
    assert all(
        getattr(capabilities, name).reason is None
        for name in CAPABILITY_NAMES
    )


def test_desktop_capabilities_preserves_independent_states_and_is_immutable():
    capabilities = DesktopCapabilities(
        hotkey_registration=CapabilityState.degraded("portal fallback"),
        hotkey_recording=CapabilityState.permission_required(
            "input permission"
        ),
        tray=CapabilityState.available(),
        window_focus=CapabilityState.unavailable("compositor policy"),
    )

    assert capabilities.hotkey_registration.is_usable
    assert not capabilities.hotkey_recording.is_usable
    assert capabilities.tray.is_available
    assert capabilities.window_focus.reason == "compositor policy"
    with pytest.raises(FrozenInstanceError):
        capabilities.tray = CapabilityState.unavailable()


def test_desktop_capabilities_rejects_non_capability_fields():
    with pytest.raises(TypeError, match="tray"):
        DesktopCapabilities(tray="available")


def test_fakes_conform_to_runtime_service_contracts():
    capabilities = DesktopCapabilities()

    assert isinstance(FakeHotkeyService(capabilities), HotkeyService)
    assert isinstance(FakeTrayBackend(capabilities), TrayBackend)
    assert isinstance(FakeAutostartService(capabilities), AutostartService)
    assert isinstance(FakeWindowService(capabilities), WindowService)
    assert isinstance(
        FakeSingleInstanceService(capabilities),
        SingleInstanceService,
    )
    assert isinstance(
        FakeSystemIntegrationService(capabilities),
        SystemIntegrationService,
    )


def test_fake_hotkey_service_registers_degraded_backend_and_can_trigger():
    calls = []
    capabilities = DesktopCapabilities(
        hotkey_registration=CapabilityState.degraded("portal fallback"),
        hotkey_recording=CapabilityState.available(),
    )
    service = FakeHotkeyService(
        capabilities,
        recorded_shortcut="ctrl+shift+w",
    )

    assert service.register("ctrl+shift+w", lambda: calls.append("called"))
    assert service.trigger("ctrl+shift+w")
    assert calls == ["called"]
    assert service.record() == "ctrl+shift+w"
    assert service.unregister("ctrl+shift+w")
    assert not service.trigger("ctrl+shift+w")


@pytest.mark.parametrize(
    "state",
    [
        CapabilityState.unavailable("no backend"),
        CapabilityState.permission_required("input permission"),
    ],
)
def test_fake_hotkey_service_rejects_unusable_registration(state):
    service = FakeHotkeyService(
        DesktopCapabilities(hotkey_registration=state)
    )

    assert not service.register("ctrl+1", lambda: None)
    assert service.registrations == {}


def test_fake_tray_backend_tracks_lifecycle_and_menu_when_degraded():
    backend = FakeTrayBackend(
        DesktopCapabilities(
            tray=CapabilityState.degraded("explicit menu only")
        )
    )

    assert backend.start(["open", "quit"])
    assert backend.running
    assert backend.menu == ("open", "quit")
    assert backend.update_menu(["open", "settings", "quit"])
    assert backend.menu == ("open", "settings", "quit")
    backend.stop()
    assert not backend.running


def test_fake_tray_backend_has_no_side_effect_when_unavailable():
    backend = FakeTrayBackend(DesktopCapabilities())

    assert not backend.start(["open"])
    assert not backend.running
    assert backend.menu == ()


def test_fake_autostart_service_changes_only_when_capability_is_usable():
    supported = FakeAutostartService(
        DesktopCapabilities(
            start_at_login=CapabilityState.degraded("session only")
        )
    )
    blocked = FakeAutostartService(
        DesktopCapabilities(
            start_at_login=CapabilityState.permission_required(
                "login item approval"
            )
        )
    )

    assert supported.set_enabled(True)
    assert supported.is_enabled()
    assert not blocked.set_enabled(True)
    assert not blocked.is_enabled()


def test_fake_window_service_uses_independent_operation_capabilities():
    service = FakeWindowService(
        DesktopCapabilities(
            window_show=CapabilityState.available(),
            window_hide=CapabilityState.degraded("best effort"),
            window_restore=CapabilityState.permission_required(
                "window permission"
            ),
            window_focus=CapabilityState.unavailable("compositor policy"),
            work_area_positioning=CapabilityState.available(),
        ),
        work_area=(10, 20, 1910, 1060),
    )

    assert service.show()
    assert service.hide()
    assert not service.restore()
    assert not service.focus()
    assert service.get_work_area() == (10, 20, 1910, 1060)
    assert service.calls == ["show", "hide", "get_work_area"]


def test_fake_single_instance_separates_exclusion_from_activation():
    service = FakeSingleInstanceService(
        DesktopCapabilities(
            single_instance_exclusion=CapabilityState.degraded("file lock"),
            single_instance_activation=CapabilityState.available(),
        )
    )

    assert service.acquire()
    assert service.is_owner
    assert service.activate_existing()
    assert service.activation_requests == 1
    service.release()
    assert not service.is_owner

    blocked = FakeSingleInstanceService(
        DesktopCapabilities(
            single_instance_exclusion=CapabilityState.available(),
            single_instance_activation=CapabilityState.permission_required(),
        )
    )
    assert blocked.acquire()
    assert not blocked.activate_existing()
    assert blocked.activation_requests == 0


def test_fake_system_integration_records_only_supported_folder_opens(
    tmp_path,
):
    supported = FakeSystemIntegrationService(
        DesktopCapabilities(open_folder=CapabilityState.available())
    )
    blocked = FakeSystemIntegrationService(DesktopCapabilities())

    assert supported.open_folder(tmp_path)
    assert supported.opened_folders == [tmp_path]
    assert not blocked.open_folder(tmp_path)
    assert blocked.opened_folders == []
