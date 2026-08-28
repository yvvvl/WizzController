from __future__ import annotations

from localization import LocalizationManager
from ui.components.target_selector import TargetSelector


class FakeWiz:
    def __init__(self, *, mode: str = "single", selected_ips=None):
        self.mode = mode
        self.selected_ips = list(selected_ips or ["192.168.1.10"])
        self.active_ip = self.selected_ips[0] if self.selected_ips else "192.168.1.10"
        self.calls: list[tuple[str, object]] = []
        self.bulbs = [
            {"ip": "192.168.1.10", "name": "Desk", "state": {"state": True}},
            {"ip": "192.168.1.11", "name": "Floor", "state": {"state": False}},
            {"ip": "192.168.1.12", "name": "Shelf", "state": {"state": True}},
        ]

    def get_bulbs_detailed(self):
        return list(self.bulbs)

    def get_target_config(self):
        return {
            "mode": self.mode,
            "active_ip": self.active_ip,
            "selected_ips": list(self.selected_ips),
        }

    def set_target_mode(self, mode: str):
        self.mode = mode
        self.calls.append(("mode", mode))

    def set_active_bulb(self, ip: str):
        self.active_ip = ip
        self.selected_ips = [ip]
        self.mode = "single"
        self.calls.append(("single", ip))

    def set_target_selection(self, ips):
        self.selected_ips = list(ips)
        self.mode = "selected"
        self.calls.append(("selected", list(ips)))


def test_refresh_keeps_partial_selection_and_shows_count():
    selector = TargetSelector(
        FakeWiz(mode="selected", selected_ips=["192.168.1.10", "192.168.1.12"]),
        i18n=LocalizationManager(preference="en"),
    )

    assert selector.selected_targets == ["192.168.1.10", "192.168.1.12"]
    assert selector.selection_status.value == "2 of 3 selected"


def test_toggle_from_partial_selection_uses_existing_controller_contract():
    wiz = FakeWiz(mode="selected", selected_ips=["192.168.1.10", "192.168.1.12"])
    selector = TargetSelector(wiz, i18n=LocalizationManager(preference="en"))

    selector.toggle_selection("192.168.1.11")

    assert wiz.calls[-1] == (
        "mode",
        "all",
    )
    assert selector.selection_status.value == "All 3 selected"


def test_empty_selector_explains_that_no_light_is_saved():
    wiz = FakeWiz()
    wiz.bulbs = []
    selector = TargetSelector(wiz, i18n=LocalizationManager(preference="es"))

    assert selector.selected_targets == []
    assert selector.selection_status.value == "Sin ampolletas guardadas"


def test_selection_notifies_visual_consumer_without_waiting_for_light_action():
    calls: list[str] = []
    selector = TargetSelector(
        FakeWiz(),
        i18n=LocalizationManager(preference="en"),
        on_selection_changed=lambda: calls.append("updated"),
    )

    selector.toggle_selection("192.168.1.11")

    assert calls
