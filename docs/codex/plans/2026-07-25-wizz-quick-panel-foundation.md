# WizZ Quick Panel Foundation Implementation Plan

Status: Completed

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a functional, compact Quick Panel that uses the existing WizZ Desktop window, lighting controller, Color Studio, action executor, favorites, tray, and localization contracts.

**Architecture:** `TrayService` forwards window intents to a framework-light `QuickPanelController`. The controller owns state snapshots, action routing, and one-window quick/full/hidden transitions. `QuickPanelView` renders those snapshots and mounts the existing `ColorPanel.main_layout`, preserving the calibrated Hue/Purity picker and its quick-colors-below-picker order without changing Color Studio.

**Tech Stack:** Python 3, Flet 0.85, pystray, pytest, existing WizZ services.

## Global Constraints

- Do not modify `core/light_controller.py`, the WiZ protocol, `config/favorites_manager.py`, the favorites JSON format, `core/action_sequence.py`, `ui/components/color_panel.py`, `ui/color_studio.py`, or the existing localization implementation/catalogs.
- Stop before continuing if a protected file proves necessary.
- Keep one `ft.Page`, one `LightController`, one `WizzApp`, and one native window.
- Support only `Individual` and `All lights`; do not add custom groups.
- Reuse the existing `ColorPanel`; do not create another HSV/RGB picker or color conversion.
- Obtain every visible label through existing i18n keys; do not add hardcoded UI copy.
- Technical comments and docstrings are English and explain invariants or constraints.
- Preserve the existing right-click tray menu, shutdown lifecycle, and close-to-tray behavior.
- Use TDD: write one behavior test, watch the expected failure, implement minimally, and rerun.
- Produce one final commit only: `feat: add WizZ Quick Panel foundation`.
- Do not push.

---

## File Structure

- Create `core/quick_panel_controller.py`: snapshot creation, action routing, and single-window transitions.
- Create `ui/quick_panel_view.py`: compact Flet view and unmodified Color Studio composition.
- Create `tests/test_quick_panel.py`: controller, view, tray, and transition behavior.
- Modify `core/background/tray_service.py`: optional Quick Panel/full-app callbacks and primary-click routing.
- Modify `main.py`: compose the full app and Quick Panel around the existing page/controller.
- Modify `docs/codex/plans/2026-07-25-wizz-quick-panel-design.md`: final implementation record.

No protected file appears in the change list.

### Task 1: Quick Panel snapshots and light actions

**Files:**
- Create: `tests/test_quick_panel.py`
- Create: `core/quick_panel_controller.py`

**Interfaces:**
- Consumes: `LightController.get_target_config()`, `get_bulbs_detailed()`, `get_tray_status()`, `set_active_bulb(ip)`, and `set_target_mode(mode)`.
- Consumes: `FavoritesManager.get_favorites()` and `ActionSequenceExecutor.execute(payload, threaded=True)`.
- Produces: `QuickPanelController.snapshot() -> dict[str, Any]`.
- Produces: `select_device(ip)`, `set_target_mode(mode)`, `turn_on()`, `turn_off()`, and `run_favorite(uid)`.

- [ ] **Step 1: Write the failing construction and snapshot test**

Create fakes whose returned device structure mirrors `get_bulbs_detailed()` and assert hand-written snapshot values:

```python
def test_controller_builds_snapshot_from_existing_services():
    controller, _page, _host, wiz, favorites, _executor = make_controller()

    snapshot = controller.snapshot()

    assert snapshot["target"]["mode"] == "single"
    assert snapshot["target"]["active_ip"] == "192.168.1.20"
    assert snapshot["devices"][0]["name"] == "Living Room"
    assert snapshot["status"]["state"]["dimming"] == 72
    assert snapshot["favorites"][0]["type"] == "rgb"
    assert wiz.snapshot_reads == ["target", "devices", "status"]
    assert favorites.reads == 1
```

The production change caught is omitting one existing service from the snapshot or returning the wrong payload under a key.

- [ ] **Step 2: Run the test and verify RED**

Run:

```text
python -m pytest -q tests/test_quick_panel.py::test_controller_builds_snapshot_from_existing_services
```

Expected: import failure for `core.quick_panel_controller`.

- [ ] **Step 3: Implement the minimal controller constructor and snapshot**

Create:

```python
class QuickPanelController:
    def __init__(
        self,
        page: Any,
        wiz: Any,
        full_app: Any,
        content_host: Any,
        *,
        favorites: Any | None = None,
        executor: Any | None = None,
    ) -> None: ...

    def snapshot(self) -> dict[str, Any]:
        return {
            "target": dict(self.wiz.get_target_config() or {}),
            "devices": list(self.wiz.get_bulbs_detailed() or []),
            "status": dict(self.wiz.get_tray_status() or {}),
            "favorites": [
                dict(item)
                for item in self.favorites.get_favorites()
                if isinstance(item, dict)
            ],
        }
```

Default dependencies are `FavoritesManager()` and
`ActionSequenceExecutor(wiz)`. Keep them injectable so unit tests do not read
the user's JSON or start hardware work.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the exact test from Step 2. Expected: PASS.

- [ ] **Step 5: Write failing tests for targeting, power, and favorites**

```python
def test_controller_selects_one_device_and_refreshes_snapshot():
    controller, *_rest, wiz, _favorites, _executor = make_controller()
    snapshot = controller.select_device("192.168.1.21")
    assert wiz.selected_ips == ["192.168.1.21"]
    assert snapshot["target"]["active_ip"] == "192.168.1.21"


def test_controller_selects_all_lights_through_existing_target_api():
    controller, *_rest, wiz, _favorites, _executor = make_controller()
    snapshot = controller.set_target_mode("all")
    assert wiz.target_modes == ["all"]
    assert snapshot["target"]["mode"] == "all"


def test_controller_routes_power_and_favorite_through_existing_executor():
    controller, _page, _host, _wiz, _favorites, executor = make_controller()
    controller.turn_on()
    controller.turn_off()
    controller.run_favorite("fav-red")
    assert executor.calls == [
        ({"type": "turn_on"}, True),
        ({"type": "turn_off"}, True),
        ({"type": "favorite", "value": "fav-red"}, True),
    ]
```

The production breaks caught are bypassing `LightController` targeting,
controlling WiZ directly, or bypassing the shared executor.

- [ ] **Step 6: Run the new tests and verify RED**

Expected: missing controller methods.

- [ ] **Step 7: Implement minimal action and refresh methods**

Validate mode with:

```python
if mode not in {"single", "all"}:
    raise ValueError(f"Unsupported target mode: {mode}")
```

After targeting, return `refresh_view()`. Power and favorite actions call only:

```python
self.executor.execute(payload, threaded=True)
```

`refresh_view()` builds a snapshot and calls `view.update_snapshot(snapshot)`
only when a view has been attached.

- [ ] **Step 8: Run all Task 1 tests**

Run:

```text
python -m pytest -q tests/test_quick_panel.py
```

Expected: PASS.

### Task 2: One-window quick, hidden, and full transitions

**Files:**
- Modify: `tests/test_quick_panel.py`
- Modify: `core/quick_panel_controller.py`

**Interfaces:**
- Consumes: one `page.window`, one `content_host`, one `full_app`.
- Produces: `attach_view(view)`, `open_quick()`, `hide_quick()`, `open_full()`, and `toggle_quick()`.
- Produces: `window_mode` with values `full`, `quick`, or `hidden`.

- [ ] **Step 1: Write the failing quick-open test**

```python
def test_open_quick_reuses_window_and_replaces_only_host_content():
    controller, page, host, *_ = make_controller()
    quick_view = object()
    controller.attach_view(quick_view)

    assert controller.open_quick() is True
    assert host.content is quick_view
    assert controller.window_mode == "quick"
    assert page.window.width == 430
    assert page.window.height == 720
    assert page.window.visible is True
    assert page.window.skip_task_bar is True
    assert page.update_count == 1
```

This catches creation of a second window or failure to switch the shared host.

- [ ] **Step 2: Run and verify RED**

Expected: `attach_view` or `open_quick` missing.

- [ ] **Step 3: Implement quick mode**

Use class constants:

```python
QUICK_WIDTH = 430
QUICK_HEIGHT = 720
QUICK_MIN_WIDTH = 380
QUICK_MIN_HEIGHT = 520
```

Capture `width`, `height`, `min_width`, `min_height`, and `resizable` once
before leaving full mode. Set the shared host's content to the attached view;
never call `ft.run`, `ft.app`, or construct another `Page`.

- [ ] **Step 4: Run and verify GREEN**

Run the focused quick-open test. Expected: PASS.

- [ ] **Step 5: Write failing hide/full/toggle tests**

```python
def test_hide_and_restore_full_app_preserve_saved_geometry():
    controller, page, host, _wiz, _favorites, _executor = make_controller()
    controller.attach_view(object())
    controller.open_quick()
    controller.hide_quick()
    assert controller.window_mode == "hidden"
    assert page.window.visible is False
    assert page.window.skip_task_bar is True

    controller.open_full()
    assert controller.window_mode == "full"
    assert host.content is controller.full_app
    assert page.window.width == 1080
    assert page.window.height == 720
    assert page.window.visible is True
    assert page.window.skip_task_bar is False


def test_toggle_quick_hides_only_a_visible_quick_panel():
    controller, page, *_ = make_controller()
    controller.attach_view(object())
    controller.toggle_quick()
    assert controller.window_mode == "quick"
    controller.toggle_quick()
    assert controller.window_mode == "hidden"
    page.window.visible = False
    controller.toggle_quick()
    assert controller.window_mode == "quick"
```

- [ ] **Step 6: Run and verify RED**

Expected: missing transition behavior or incorrect geometry.

- [ ] **Step 7: Implement hide/full/toggle**

`open_full()` restores the captured geometry, sets the full app into the same
host, makes the window visible/focused, and calls the full app's
`set_viewport(width, height, update=False)` when available. `hide_quick()`
changes visibility only; it does not destroy services.

- [ ] **Step 8: Run Task 2 tests and verify GREEN**

Expected: PASS.

### Task 3: Compact Flet view and exact Color Studio reuse

**Files:**
- Modify: `tests/test_quick_panel.py`
- Create: `ui/quick_panel_view.py`

**Interfaces:**
- Consumes: `QuickPanelController`, shared `wiz`, existing i18n manager, and an optional injected `ColorPanel`.
- Produces: `QuickPanelView(ft.Column)`.
- Produces: `update_snapshot(snapshot)` and `set_language(language=None)`.
- Uses: the exact existing `ColorPanel.main_layout`; no copied palette or conversion.

- [ ] **Step 1: Write the failing view-construction test**

```python
def test_view_builds_compact_sections_from_i18n_and_existing_color_studio():
    i18n = LocalizationManager(preference="en")
    studio = SimpleNamespace(main_layout=ft.Container(data="existing-color-studio"))
    controller = RecordingQuickController()

    view = QuickPanelView(
        controller,
        object(),
        i18n=i18n,
        color_panel=studio,
    )

    assert view.title.value == "Quick Panel"
    assert view.power_on.text == "ON"
    assert view.power_off.text == "OFF"
    assert view.color_host.content is studio.main_layout
    assert view.controls.index(view.color_host) < view.controls.index(view.favorites_section)
```

This catches hardcoded copy and accidental construction of a second picker.

- [ ] **Step 2: Run and verify RED**

Expected: import failure for `ui.quick_panel_view`.

- [ ] **Step 3: Implement the minimal view**

The Focused stack is:

```text
header
device selector
Individual / All lights
ON / OFF
existing ColorPanel.main_layout
quick favorites
```

Use existing keys only:

- `quick.title`;
- `common.online`, `common.offline`;
- `routines.target.single`, `tray.all_lights`;
- `home.on`, `home.off`;
- `quick.favorites`;
- `favorites.empty`.

The default studio is:

```python
self.color_panel = color_panel or ColorPanel(wiz, i18n=self.i18n)
self.color_panel.set_viewport(390, 620)
self.color_host = ft.Container(content=self.color_panel.main_layout)
```

`ColorPanel.color_section` already orders the calibrated palette before
`quick_color_row`; do not reorder or copy those controls.

- [ ] **Step 4: Run and verify GREEN**

Run the focused construction test. Expected: PASS.

- [ ] **Step 5: Write failing snapshot and callback tests**

```python
def test_view_updates_devices_modes_status_and_favorites():
    view, controller = make_view()
    view.update_snapshot(SNAPSHOT)
    assert [option.key for option in view.device_selector.options] == [
        "192.168.1.20",
        "192.168.1.21",
    ]
    assert view.device_selector.value == "192.168.1.20"
    assert view.online_status.value == "Online"
    assert len(view.favorite_row.controls) == 2

    view.device_selector.on_select(
        SimpleNamespace(control=SimpleNamespace(value="192.168.1.21"))
    )
    view.all_lights.on_click(None)
    view.power_on.on_click(None)
    view.power_off.on_click(None)
    view.favorite_row.controls[0].on_click(None)
    assert controller.calls == [
        ("device", "192.168.1.21"),
        ("target", "all"),
        ("power", "on"),
        ("power", "off"),
        ("favorite", "fav-red"),
    ]
```

This catches incorrect event wiring and stale rendered state.

- [ ] **Step 6: Run and verify RED**

Expected: missing rendering/callback behavior.

- [ ] **Step 7: Implement snapshot rendering and callbacks**

Create `ft.DropdownOption(key=ip, text=name)` from device snapshots. User
device/favorite names remain unchanged; built-in favorite names pass through
`translated_favorite_name(i18n, favorite)`. Rebuild only the favorite row, not
the entire Color Studio, on snapshot changes.

- [ ] **Step 8: Run Task 3 tests and existing Color Studio tests**

Run:

```text
python -m pytest -q tests/test_quick_panel.py tests/test_color_panel_studio.py
```

Expected: PASS.

### Task 4: Tray callbacks, single/double click, and Linux fallback

**Files:**
- Modify: `tests/test_quick_panel.py`
- Modify: `core/background/tray_service.py`

**Interfaces:**
- Extends `TrayService.__init__` with optional `on_open_quick` and `on_open_full` callbacks.
- Produces: `_open_quick_panel()`, `_open_full_app()`, and deferred Windows primary-click handling.
- Preserves all behavior when callbacks are `None`.

- [ ] **Step 1: Write the failing callback/menu test**

```python
def test_tray_menu_keeps_existing_actions_and_adds_quick_panel():
    tray = make_fake_menu_tray(
        on_open_quick=lambda: None,
        on_open_full=lambda: None,
        language="en",
    )
    menu = tray._build_menu()
    labels = [item.text for item in menu.items if hasattr(item, "text")]
    assert labels[:3] == ["Quick Panel", "Open WizZ Desktop", "Hide WizZ"]
    assert "Turn on" in labels
    assert "Turn off" in labels
    assert "Exit" in labels
```

This catches removal/reordering of established right-click behavior.

- [ ] **Step 2: Run and verify RED**

Expected: constructor rejects new callbacks or menu lacks Quick Panel.

- [ ] **Step 3: Add optional callbacks and menu items**

Use `tray.quick_panel` and `quick.open_full`. On non-Windows, make the Quick
Panel item the default action. Keep a visible item for AppIndicator/Wayland,
where a default primary action may not be available.

- [ ] **Step 4: Run and verify GREEN**

Expected: PASS without changing existing tray tests.

- [ ] **Step 5: Write the failing Windows click arbitration test**

Use a deterministic fake timer because the real delay is an OS boundary:

```python
def test_windows_primary_click_defers_quick_and_double_click_opens_full(monkeypatch):
    quick_calls: list[str] = []
    full_calls: list[str] = []
    timers: list[FakeTimer] = []
    tray = make_tray(
        on_open_quick=lambda: quick_calls.append("quick"),
        on_open_full=lambda: full_calls.append("full"),
    )
    monkeypatch.setattr(tray_module.os, "name", "nt")
    monkeypatch.setattr(tray_module.threading, "Timer", lambda delay, fn: timers.append(FakeTimer(delay, fn)) or timers[-1])

    tray._handle_tray_primary_click()
    assert quick_calls == []
    timers[0].fire()
    assert quick_calls == ["quick"]

    tray._handle_tray_primary_click()
    tray._handle_tray_primary_click()
    assert timers[-1].cancelled is True
    assert full_calls == ["full"]
```

This catches opening the compact window before the double-click decision and
the resulting visual flash.

- [ ] **Step 6: Run and verify RED**

Expected: legacy double-click toggle behavior does not call the callbacks.

- [ ] **Step 7: Implement deferred single-click routing**

When Quick Panel callbacks exist:

- first Windows click starts a daemon `threading.Timer`;
- timer completion schedules `on_open_quick`;
- a second click inside the system interval cancels the timer and schedules
  `on_open_full`;
- non-Windows primary action schedules `on_open_quick`;
- absent callbacks retain the current legacy `toggle_window()` behavior.

Callback invocation must use `_schedule_page_coroutine()` first and a
synchronous fallback only when no live Flet loop exists. The comment must
explain the tray-thread/event-loop boundary.

- [ ] **Step 8: Run tray and Quick Panel tests**

Run:

```text
python -m pytest -q tests/test_quick_panel.py tests/test_tray_window_restore.py tests/test_tray_branding.py
```

Expected: PASS.

### Task 5: Compose the single Page in `main.py`

**Files:**
- Modify: `main.py`
- Modify: `tests/test_quick_panel.py`

**Interfaces:**
- Consumes: existing `WizzApp`, `LightController`, `TrayService`, and Flet `Page`.
- Produces: one shared `ft.Container` host, one `QuickPanelController`, and one `QuickPanelView`.
- Fans each WiZ state callback to both `WizzApp.update_ui` and `QuickPanelController.update_state`.

- [ ] **Step 1: Write the failing state-fanout test**

Extract a small pure helper:

```python
def _update_runtime_views(
    app: Any,
    quick_panel: Any,
    state: dict[str, Any],
) -> None:
    app.update_ui(state)
    quick_panel.update_state(state)
```

Test:

```python
def test_runtime_state_updates_full_and_quick_views():
    full = RecordingStateConsumer()
    quick = RecordingStateConsumer()
    state = {"state": True, "dimming": 72}
    _update_runtime_views(full, quick, state)
    assert full.states == [state]
    assert quick.states == [state]
```

This catches connecting the sole `LightController` callback to only one UI.

- [ ] **Step 2: Run and verify RED**

Expected: `_update_runtime_views` import failure.

- [ ] **Step 3: Implement state fanout and one-host composition**

In `main(page)`:

```python
app = WizzApp(page, wiz, hotkeys_manager=hotkeys)
content_host = ft.Container(content=app, expand=True)
quick_controller = QuickPanelController(page, wiz, app, content_host)
quick_view = QuickPanelView(quick_controller, wiz, i18n=i18n)
quick_controller.attach_view(quick_view)
```

Pass:

```python
on_open_quick=quick_controller.toggle_quick
on_open_full=quick_controller.open_full
```

to `TrayService`. Add only `content_host` to the page. The existing resize
handler remains the full app handler; `open_full()` reapplies the restored
viewport.

Set the light callback to dispatch `_update_runtime_views(app,
quick_controller, state)`. Expose the controller on
`page._wizz_quick_panel` alongside the existing runtime references for
diagnostics.

- [ ] **Step 4: Run focused tests and compile**

Run:

```text
python -m pytest -q tests/test_quick_panel.py tests/test_main_instance_activation.py
python -m compileall -q main.py app_meta.py core config ui localization tests tools
```

Expected: PASS.

### Task 6: Documentation, verification, manual smoke, and final commit

**Files:**
- Modify: `docs/codex/plans/2026-07-25-wizz-quick-panel-design.md`
- Inspect: every changed file

**Interfaces:**
- Produces: complete `Implementation record`.
- Produces: one validated commit; no push.

- [ ] **Step 1: Update the implementation record**

Replace the placeholder with exact:

- files modified;
- final controller/view/tray/main flow;
- any deviation from the approved design;
- tests and results;
- risks encountered;
- next steps, including visual refinement and real-device/Linux coverage.

- [ ] **Step 2: Run protected-boundary and temporary-file checks**

Run:

```text
git status --short
git diff --name-only
```

Fail the gate if the diff includes:

```text
core/light_controller.py
core/action_sequence.py
core/wiz_protocol.py
config/favorites_manager.py
ui/components/color_panel.py
ui/color_studio.py
localization/
```

Also fail if cache, generated, log, or temporary files appear.

- [ ] **Step 3: Run mandatory automated validation**

Run:

```text
python -m compileall -q main.py app_meta.py core config ui localization tests tools
python -m pytest -q
python tools/i18n_audit.py
git diff --check
```

Expected:

- compile exits 0;
- all tests pass;
- i18n catalogs match and no visible hardcoded strings are reported;
- diff check exits 0.

- [ ] **Step 4: Run the desktop smoke**

Run `python main.py`, confirm the process and tray remain healthy, and manually
check:

1. tray icon appears;
2. Quick Panel opens and closes;
3. full app restores;
4. only one window exists;
5. right-click menu still works.

If GUI interaction cannot be completed automatically, record the exact
automated startup duration and list the remaining human checks without
claiming they passed.

- [ ] **Step 5: Show the required pre-commit evidence**

Run and report:

```text
git status
git diff --stat
git diff --check
```

Confirm the exact file list.

- [ ] **Step 6: Stage only the approved files**

```text
git add core/quick_panel_controller.py ui/quick_panel_view.py core/background/tray_service.py main.py tests/test_quick_panel.py docs/codex/plans/2026-07-25-wizz-quick-panel-design.md docs/codex/plans/2026-07-25-wizz-quick-panel-foundation.md
git diff --cached --check
git diff --cached --stat
```

- [ ] **Step 7: Create the single final commit**

```text
git commit -m "feat: add WizZ Quick Panel foundation"
```

- [ ] **Step 8: Verify the commit and stop**

Run:

```text
git status --short --branch
git show --stat --oneline --summary HEAD
```

Do not push. Wait for review.
