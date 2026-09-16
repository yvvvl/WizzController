from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy

from core.dev_virtual_lights import VirtualLightController
from qt_ui.bridge import WizzBridge


@pytest.fixture(scope="module", autouse=True)
def qt_application():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


@pytest.fixture()
def bridge():
    controller = VirtualLightController(3)
    controller.start()
    view_model = WizzBridge(controller)
    yield view_model
    controller.stop()


def test_qt_bridge_exposes_virtual_lights(bridge):
    assert bridge.totalCount == 3
    assert bridge.selectedCount == 3
    assert bridge.lights.rowCount() == 3
    assert bridge.scenes.rowCount() >= 33
    assert bridge.statusLine.endswith("RGB + Blancos")


def test_qt_settings_bridge_keeps_control_preferences_available(bridge):
    bridge.setSliderInterval(90)

    assert bridge.sliderInterval == 90


def test_qt_appearance_preferences_update_the_bridge_state(bridge):
    initial_theme = bridge.themeName
    initial_motion = bridge.reducedMotion

    bridge.setTheme("ocean")
    assert bridge.themeName == "ocean"

    bridge.setReducedMotion(not initial_motion)
    assert bridge.reducedMotion is (not initial_motion)
    bridge.setReducedMotion(initial_motion)
    bridge.setTheme(initial_theme)


def test_qt_update_channel_is_persisted(bridge):
    initial_channel = bridge.updateChannel

    bridge.setUpdateChannel("beta")
    assert bridge.updateChannel == "beta"

    bridge.setUpdateChannel(initial_channel)


def test_qt_bridge_selection_updates_immediately(bridge):
    first_ip = bridge.lights._items[0]["ip"]

    bridge.toggleLight(first_ip)

    assert bridge.selectedCount == 2
    assert not bridge.lights._items[0]["selected"]


def test_qt_bridge_uses_the_live_rgb_channels_for_light_tint():
    state = WizzBridge._state_for_bulb(
        {
            "state": True,
            "raw_state": {"state": True, "r": 255, "g": 0, "b": 0},
            # This stands in for the lossy RGBTW reconstruction.  It must
            # never override fresh channels received from the bulb.
            "color_rgb": (124, 167, 181),
        }
    )

    assert WizzBridge._display_color(state) == "#ff0000"


def test_qt_quick_panel_target_controls_use_shared_controller(bridge):
    second_ip = bridge.lights._items[1]["ip"]

    bridge.setTargetMode("all")
    assert bridge.targetMode == "all"

    bridge.setActiveLight(second_ip)
    assert bridge.activeLightIp == second_ip


def test_qt_bridge_commands_reuse_the_shared_controller(bridge):
    bridge.toggleMaster()
    assert bridge.controller.get_state()["state"] is False

    bridge.queueBrightness(63)
    assert bridge.brightness == 63
    bridge._flush_brightness()
    assert bridge.controller.get_state()["dimming"] == 63


def test_qt_bridge_throttles_white_transport_while_preview_stays_local(bridge):
    bridge.setWhite(3120)

    assert bridge._pending_white == 3120
    assert bridge.whiteKelvin == 3120

    bridge._flush_white()

    assert bridge._pending_white is None
    assert bridge.controller.get_state()["temp"] == 3120


def test_qt_bridge_records_and_reapplies_recent_values(bridge):
    bridge.setRgb(40, 80, 120)
    bridge.commitCurrentColor()
    bridge.commitWhite(2700)

    assert bridge.recents.rowCount() == 2
    assert bridge.recents._items[0]["uid"] == "white:2700"

    bridge.applyRecent("rgb:#285078")
    assert bridge.colorHex == "#285078"

    bridge.clearRecents()
    assert bridge.recents.rowCount() == 0


def test_qt_bridge_accepts_precise_hex_values(bridge):
    assert bridge.setHex("12ABEF")
    assert bridge.colorHex == "#12abef"
    assert not bridge.setHex("not-a-colour")


def test_qt_bridge_keeps_color_preview_immediate_and_throttles_transport(bridge):
    color_updates = QSignalSpy(bridge.colorChanged)
    global_updates = QSignalSpy(bridge.stateChanged)
    bridge.setRgb(12, 128, 240)

    assert bridge.colorHex == "#0c80f0"
    assert bridge._pending_rgb == (12, 128, 240)
    assert color_updates.count() == 0
    assert global_updates.count() == 0

    bridge._flush_rgb()

    assert bridge._pending_rgb is None
    assert bridge.controller.get_state()["r"] == 12
    assert color_updates.count() == 1


def test_rgb_acknowledgements_do_not_rebuild_models_during_drag(bridge, monkeypatch):
    rebuilds = 0

    def count_rebuilds():
        nonlocal rebuilds
        rebuilds += 1

    monkeypatch.setattr(bridge, "_refresh_library_models", count_rebuilds)

    for value in range(24):
        bridge.setRgb(value * 10, 120, 240)
        bridge._flush_rgb()

    assert rebuilds == 0
    assert bridge._model_refresh_timer.isActive()
    bridge._model_refresh_timer.stop()


def test_qt_bridge_applies_builtin_scene_by_id(bridge):
    bridge.applyScene("wiz:18")

    assert bridge.controller.get_state()["sceneId"] == 18


def test_qt_bridge_favorite_crud_refreshes_the_qml_model(bridge):
    class MemoryFavorites:
        def __init__(self):
            self.items = []

        def seed_defaults(self):
            return None

        def get_favorites(self):
            return self.items

        def get_favorite(self, uid):
            return next((item for item in self.items if item["id"] == uid), None)

        def add_favorite(self, name, kind, value, icon):
            item = {"id": "memory-favorite", "name": name, "type": kind, "value": value, "icon": icon}
            self.items.append(item)
            return item

        def update_favorite(self, uid, name, kind, value, icon):
            item = self.get_favorite(uid)
            if not item:
                return False
            item.update(name=name, type=kind, value=value, icon=icon)
            return True

        def remove_favorite(self, uid):
            before = len(self.items)
            self.items = [item for item in self.items if item["id"] != uid]
            return len(self.items) != before

    bridge._favorites_manager = MemoryFavorites()

    uid = bridge.upsertFavorite("", "Prueba RGB", "rgb", "#12ABEF")
    assert uid == "memory-favorite"
    assert bridge.favorites._items[0]["rawValue"] == "#12ABEF"
    assert bridge.favorites._items[0]["kind"] == "rgb"

    assert bridge.upsertFavorite(uid, "Prueba blanca", "white", "3120") == uid
    assert bridge.favorites._items[0]["subtitle"] == "3120K"

    assert bridge.upsertFavorite(uid, "Escena lenta", "scene", '{"sceneId":18,"speed":65}') == uid
    assert '"speed":65' in bridge.favorites._items[0]["rawValue"]

    assert bridge.upsertFavoriteFromScene(uid, "Cine rápido", "wiz:18", 142) == uid
    stored_scene = json.loads(bridge.favorites._items[0]["rawValue"])
    assert bridge.favorites._items[0]["kind"] == "scene"
    assert stored_scene == {"sceneId": 18, "speed": 142}

    assert bridge.deleteFavorite(uid)
    assert bridge.favorites.rowCount() == 0


def test_qt_bridge_reports_when_the_current_color_is_saved(bridge):
    class MemoryFavorites:
        def __init__(self):
            self.items = []

        def seed_defaults(self):
            return None

        def get_favorites(self):
            return self.items

        def add_favorite(self, name, kind, value, icon):
            item = {"id": "current", "name": name, "type": kind, "value": value, "icon": icon}
            self.items.append(item)
            return item

    bridge._favorites_manager = MemoryFavorites()
    bridge.setRgb(18, 171, 239)
    assert not bridge.currentFavoriteSaved

    bridge.saveCurrentFavorite()
    assert bridge.currentFavoriteSaved


def test_qt_bridge_scene_speed_and_custom_scene_crud(bridge):
    class MemoryScenes:
        def __init__(self):
            self.items = []

        def get_scenes(self):
            return self.items

        def get_scene(self, uid):
            return next((item for item in self.items if item["id"] == uid), None)

        def add_scene(self, name, mode, value, icon="AUTO_AWESOME"):
            item = {"id": "memory-scene", "name": name, "mode": mode, "value": value, "icon": icon}
            self.items.append(item)
            return item

        def update_scene(self, uid, name, mode, value):
            item = self.get_scene(uid)
            if not item:
                return False
            item.update(name=name, mode=mode, value=value)
            return True

        def remove_scene(self, uid):
            before = len(self.items)
            self.items = [item for item in self.items if item["id"] != uid]
            return len(self.items) != before

    bridge._scenes_manager = MemoryScenes()

    uid = bridge.upsertCustomScene("", "Atmósfera", "rgb", "#12ABEF", 72, 100)
    assert uid == "memory-scene"
    assert bridge.custom_scenes._items[0]["kind"] == "rgb"
    assert bridge._scenes_manager.items[0]["value"]["dimming"] == 72

    bridge.queueSceneSpeed(4, 137)
    bridge._flush_scene()
    assert bridge.controller.get_state()["sceneId"] == 4
    assert bridge.controller.get_state()["speed"] == 137

    assert bridge.deleteCustomScene(uid)
    assert bridge.custom_scenes.rowCount() == 0


def test_qt_bridge_routine_editor_crud_preserves_visual_steps(bridge):
    class MemoryRoutines:
        def __init__(self):
            self.items = []

        def get_routines(self):
            return self.items

        def get_routine(self, uid):
            return next((item for item in self.items if item["id"] == uid), None)

        def normalize_actions(self, actions):
            return [item for item in actions if isinstance(item, dict) and item.get("type")]

        def add_routine(self, name, actions, description="", color="#5f91ff", icon="AUTO_AWESOME_ROUNDED"):
            item = {
                "id": "memory-routine", "name": name, "description": description,
                "color": color, "icon": icon, "actions": actions,
            }
            self.items.append(item)
            return item

        def update_routine(self, uid, **fields):
            item = self.get_routine(uid)
            if not item:
                return False
            item.update(fields)
            return True

        def remove_routine(self, uid):
            before = len(self.items)
            self.items = [item for item in self.items if item["id"] != uid]
            return len(self.items) != before

        def duplicate_routine(self, uid):
            source = self.get_routine(uid)
            if not source:
                return None
            copy = dict(source, id="memory-routine-copy", name=source["name"] + " copia")
            self.items.append(copy)
            return copy

        def reset_defaults(self):
            self.items = []

    bridge._routines_manager = MemoryRoutines()
    actions = '[{"type":"turn_on"},{"type":"wait","value":500},{"type":"condition","value":"power_on"}]'

    uid = bridge.upsertRoutine("", "Tarde", "Luz cálida gradual", "#FF8844", actions)

    assert uid == "memory-routine"
    assert bridge.routines.rowCount() == 1
    assert bridge.routines._items[0]["subtitle"] == "Luz cálida gradual · 3 pasos"
    assert '"condition"' in bridge.routines._items[0]["rawValue"]

    bridge.controller.set_scene(18, speed=135)
    bridge.controller.set_brightness(64)
    assert bridge.captureCurrentRoutine() == "memory-routine"
    captured = bridge._routines_manager.items[-1]
    assert captured["name"] == "Estado actual"
    assert {step["type"] for step in captured["actions"]} == {"turn_on", "scene", "brightness"}
    assert captured["actions"][1]["value"] == {"sceneId": 18, "speed": 135}

    assert bridge.duplicateRoutine(uid) == "memory-routine-copy"
    assert bridge.routines.rowCount() == 3
    assert bridge.deleteRoutine(uid)
    assert bridge.routines.rowCount() == 1


def test_qt_bridge_hotkey_assignment_refreshes_assigned_rows(bridge):
    class MemoryHotkeys:
        def __init__(self):
            self.values = {}

        def assign_hotkey(self, action_id, combo):
            normalized = combo.lower().replace(" ", "")
            self.values[action_id] = normalized
            return {"ok": True, "message": "Atajo guardado."}

        def clear_hotkey(self, action_id):
            self.values.pop(action_id, None)

        def configured_rows(self):
            return [
                {"id": action_id, "name": "Alternar encendido", "group": "General", "combo": combo}
                for action_id, combo in self.values.items()
            ]

        def backend_status(self):
            return "simulado"

        def stop(self):
            return None

    bridge._hotkeys_manager = MemoryHotkeys()

    assert bridge.saveHotkey("toggle", "CTRL + ALT + L") == "Atajo guardado."
    assert bridge.hotkeys.rowCount() == 1
    assert bridge.hotkeys._items[0]["rawValue"] == "ctrl+alt+l"

    bridge.clearHotkey("toggle")
    assert bridge.hotkeys.rowCount() == 0
