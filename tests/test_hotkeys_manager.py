import copy
import threading

from config.base_manager import JsonManager
from config.hotkeys_manager import HotkeysManager
from core.global_hotkeys import WindowsNativeHotkeyBackend


class FakeWiz:
    def __init__(self):
        self.calls = []
        self.state = {"dimming": 50}

    def turn_on(self): self.calls.append(("on",))
    def turn_off(self): self.calls.append(("off",))
    def toggle(self): self.calls.append(("toggle",))
    def reset_light(self): self.calls.append(("reset",))
    def set_target_mode(self, mode): self.calls.append(("target", mode))
    def set_brightness(self, pct): self.calls.append(("brightness", int(pct))); self.state["dimming"] = int(pct)
    def set_rgb(self, r, g, b): self.calls.append(("rgb", int(r), int(g), int(b)))
    def set_white(self, kelvin): self.calls.append(("white", int(kelvin)))
    def set_white_percent(self, pct): self.calls.append(("white_pct", int(pct)))
    def set_scene(self, sid, speed=None): self.calls.append(("scene", int(sid), speed))
    def get_state(self): return dict(self.state)


def _temp_json(monkeypatch, tmp_path):
    def fake_init(self, filename, default_data=None):
        self.base_dir = str(tmp_path)
        self.json_dir = str(tmp_path)
        self.filepath = str(tmp_path / filename)
        self.lock = threading.Lock()
        self.data = copy.deepcopy(default_data if default_data is not None else {})
    monkeypatch.setattr(JsonManager, "__init__", fake_init)


def test_validate_rejects_system_hotkeys():
    assert HotkeysManager.validate_hotkey("alt+tab")[0] is False
    assert HotkeysManager.validate_hotkey("win+l")[0] is False
    assert HotkeysManager.validate_hotkey("a")[0] is False
    assert HotkeysManager.validate_hotkey("ctrl+alt+a")[0] is True


def test_assign_replaces_conflict_without_keyboard_hooks(tmp_path, monkeypatch):
    _temp_json(monkeypatch, tmp_path)
    manager = HotkeysManager(FakeWiz(), auto_apply=False)
    r1 = manager.assign_hotkey("toggle", "ctrl+alt+l")
    r2 = manager.assign_hotkey("off", "ctrl+alt+l")
    assert r1["ok"] is True
    assert r2["ok"] is True
    assert manager.get_hotkey("toggle") is None
    assert manager.get_hotkey("off") == "ctrl+alt+l"


def test_execute_static_action_uses_action_sequence(tmp_path, monkeypatch):
    _temp_json(monkeypatch, tmp_path)
    wiz = FakeWiz()
    manager = HotkeysManager(wiz, auto_apply=False)
    manager.execute_action("color_hex_ff00aa")
    import time
    deadline = time.time() + 1
    while time.time() < deadline and not wiz.calls:
        time.sleep(0.02)
    assert ("rgb", 255, 0, 170) in wiz.calls


def test_cooldown_prevents_repeated_fire(tmp_path, monkeypatch):
    _temp_json(monkeypatch, tmp_path)
    wiz = FakeWiz()
    manager = HotkeysManager(wiz, auto_apply=False)
    manager.set_cooldown_ms(900)
    manager.execute_action("toggle")
    manager.execute_action("toggle")
    import time
    time.sleep(0.1)
    assert wiz.calls.count(("toggle",)) == 1


def test_native_backend_parser_supports_common_windows_combos():
    parsed = WindowsNativeHotkeyBackend.parse_combo("ctrl+alt+up")
    assert parsed is not None
    modifiers, vk = parsed
    assert modifiers & WindowsNativeHotkeyBackend.MOD_CONTROL
    assert modifiers & WindowsNativeHotkeyBackend.MOD_ALT
    assert vk == 0x26


def test_plus_key_normalizes_to_supported_name():
    assert HotkeysManager.normalize_hotkey("ctrl+alt+plus") == "ctrl+alt+plus"
    assert HotkeysManager.validate_hotkey("ctrl+alt+plus")[0] is True


class _FakeNativeBackend:
    def __init__(self, *, fail_second=False):
        self.fail_second = fail_second
        self.successful_entries = []
        self.failed_entries = []
        self.stop_calls = 0
        self.start_calls = 0

    def stop(self):
        self.stop_calls += 1

    def start(self, entries):
        self.start_calls += 1
        if self.fail_second and len(entries) > 1:
            self.successful_entries = [dict(entries[0])]
            self.failed_entries = [
                {**dict(entries[1]), "error": "Hot key is already registered.", "error_code": 1409}
            ]
        else:
            self.successful_entries = [dict(row) for row in entries]
            self.failed_entries = []
        return bool(self.successful_entries)


class _FakeKeyboard:
    def __init__(self):
        self.added = []
        self.removed = []

    def add_hotkey(self, combo, callback, *, suppress, trigger_on_release):
        handle = f"handle:{combo}"
        self.added.append((combo, suppress, trigger_on_release, callback))
        return handle

    def remove_hotkey(self, handle):
        self.removed.append(handle)


def test_partial_native_registration_uses_keyboard_only_for_failed(tmp_path, monkeypatch):
    _temp_json(monkeypatch, tmp_path)
    import config.hotkeys_manager as hotkeys_module

    monkeypatch.setattr(hotkeys_module.os, "name", "nt")
    fake_keyboard = _FakeKeyboard()
    monkeypatch.setattr(hotkeys_module, "_keyboard", fake_keyboard)

    manager = HotkeysManager(FakeWiz(), auto_apply=False)
    manager.data["hotkeys"] = {
        "toggle": "ctrl+alt+l",
        "bri_up": "ctrl+alt+up",
    }
    manager._native_backend = _FakeNativeBackend(fail_second=True)

    manager.apply_hooks()

    assert manager.last_backend == "hybrid"
    assert [row[0] for row in fake_keyboard.added] == ["ctrl+alt+up"]
    assert manager.registration_report() == {
        "backend": "hybrid",
        "total": 2,
        "native": 1,
        "keyboard": 1,
        "failed": [],
    }
    assert "2/2" in manager.backend_status()
    assert "fallback keyboard" in (manager.last_warning or "")


def test_reregister_removes_old_keyboard_handles(tmp_path, monkeypatch):
    _temp_json(monkeypatch, tmp_path)
    import config.hotkeys_manager as hotkeys_module

    monkeypatch.setattr(hotkeys_module.os, "name", "posix")
    fake_keyboard = _FakeKeyboard()
    monkeypatch.setattr(hotkeys_module, "_keyboard", fake_keyboard)

    manager = HotkeysManager(FakeWiz(), auto_apply=False)
    manager.data["hotkeys"] = {"toggle": "ctrl+alt+l"}

    manager.apply_hooks()
    first_handle = manager._handles[0]
    manager.apply_hooks()

    assert first_handle in fake_keyboard.removed
    assert len(manager._handles) == 1
    assert manager.backend_status().endswith("1/1")


def test_hotkey_conflict_error_is_human_readable():
    text = HotkeysManager._friendly_hotkey_error(
        {"error": "Hot key is already registered.", "error_code": 1409}
    )
    assert text == "ya está en uso por otra aplicación"
