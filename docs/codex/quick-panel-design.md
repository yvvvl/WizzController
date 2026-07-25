# WizZ Quick Panel design

## Objective

Design and implement the first Quick Panel for WizZ Desktop v1.2.0. The panel
is a compact lighting control center opened from the system tray; it is not a
replacement for the existing tray context menu or the full desktop
application.

The approved visual direction is the **Focused stack**:

1. current device and target mode;
2. persistent ON and OFF actions;
3. Color and White modes;
4. the existing calibrated Color Studio picker;
5. quick colors below the picker;
6. brightness;
7. quick favorites.

The quick-color row must appear below the calibrated picker, matching the
existing Color Studio interaction order. Color Studio remains the source of
truth for RGB selection because its Hue/Purity model is calibrated for WiZ
bulbs and is more accurate than a generic HSV picker.

## Protected boundaries

This feature must not modify:

- `core/light_controller.py`;
- the WiZ protocol implementation;
- `config/favorites_manager.py`;
- `core/action_sequence.py`;
- Color Studio internals in `ui/color_studio.py` or
  `ui/components/color_panel.py`;
- the persisted favorites JSON format;
- the existing localization implementation.

All Quick Panel copy must use the existing localization system. Existing keys
must be reused when possible. If new copy requires new keys, both English and
Spanish catalogs must receive matching entries; no parallel translation
mechanism or hardcoded visible English copy is allowed.

The Quick Panel will consume existing public behavior. If implementation
proves that one of the protected modules must change, work must stop and the
required scope expansion must be explained before proceeding.

## Current tray architecture

`main.py` creates the single Flet `Page`, the shared `LightController`, the
full `WizzApp`, and `TrayService`.

`core/background/tray_service.py` owns the `pystray.Icon` lifecycle and builds
the current context menu. Its actions use `ActionSequenceExecutor` and refresh
the menu after commands. The menu already exposes:

- ON, OFF, and toggle;
- brightness presets and deltas;
- quick RGB and White values;
- WiZ scenes;
- favorites;
- routines;
- target mode selection;
- show, hide, and exit.

Window visibility is synchronized through the Flet page. Windows additionally
uses the native restore helper when needed. The current primary action is
platform-dependent: Windows reserves an invisible default menu item for its
click handling, while non-Windows backends use the visible Show action as the
default.

The Quick Panel will preserve the existing right-click menu and exit
lifecycle.

## Existing services

### Light control

`LightController` is the shared lighting service. The Quick Panel can use its
existing public surface:

- `set_target_mode("single" | "all")`;
- `set_active_bulb(ip)`;
- `get_target_config()`;
- `get_bulbs_detailed()`;
- `get_tray_status()`;
- `get_kelvin_range()`;
- the existing RGB, White, brightness, power, and favorite application
  methods.

The current group contract means **all available target lights**. It does not
support an arbitrary selected subset. The v1.2.0 panel will therefore offer
`Individual` and `All lights`; custom partial groups are out of scope because
they would require changing the protected `LightController`.

### Action execution

`ActionSequenceExecutor` is the existing non-blocking command path used by the
tray and Color Studio. The Quick Panel controller will reuse it for power and
favorite commands instead of duplicating command sequencing or creating its
own worker model.

### Favorites

`FavoritesManager` owns the stable favorite persistence contract:

- RGB: HEX string;
- White: Kelvin integer;
- Scene: scene identifier and optional speed;
- Brightness: percentage integer.

The Quick Panel will read favorites through `FavoritesManager` and execute
them through the existing light/action path. It will not edit favorites,
change their payload, or write a new JSON shape.

### Color Studio

`ColorPanel` provides the mature Color Studio experience:

- calibrated perceptual RGB palette;
- Hue/Purity and HEX handling;
- quick colors;
- real device Kelvin limits;
- White presets;
- brightness;
- throttled live application;
- local edit guards and state synchronization.

Creating another color picker would duplicate calibration and risk producing
colors that do not match WiZ bulbs accurately. The Quick Panel will instead
compose an unmodified `ColorPanel` and mount its existing control layout.

## Proposed architecture

```text
System tray
    |
    v
QuickPanelController
    |--------------------------|
    v                          v
QuickPanelView          ActionSequenceExecutor
    |                          |
    v                          v
Existing ColorPanel       LightController
    |
    v
LightController
```

### `QuickPanelController`

The controller is UI-framework-light and owns:

- the current window mode: hidden, quick, or full;
- the saved full-window geometry;
- compact-window geometry;
- active device and target mode changes;
- ON and OFF execution;
- quick favorite loading and execution;
- status snapshots for the view;
- tray primary-click coordination;
- safe scheduling from the tray thread into the Flet event loop.

It receives the existing `Page`, `LightController`, full `WizzApp`, and the
shared content host. It does not own a second light controller or persist a
new configuration format.

### `QuickPanelView`

The view is a compact Flet control tree based on the approved Focused stack.
It receives user actions through controller callbacks and renders state
snapshots without owning device discovery or WiZ protocol behavior.

The visible sections are:

- device selector and online state;
- `Individual` / `All lights`;
- ON / OFF;
- active Color Studio content;
- quick favorites.

Every visible label is resolved through the existing i18n manager. User-created
device and favorite names are preserved.

### Color Studio composition

The Quick Panel creates one unmodified `ColorPanel` as the behavior owner and
mounts its existing responsive `main_layout` inside the compact content zone.
This preserves:

- the calibrated Hue/Purity picker;
- HEX/precise controls;
- the existing picker-to-quick-colors order;
- real Kelvin limits and White presets;
- brightness and live-apply throttling.

The foundation does not duplicate, fork, or alter Color Studio internals.
Further compact-only tree reconstruction is deferred until it can be provided
without changing the protected component.

## Window and tray behavior

WizZ Desktop will continue to use one native Flet window:

- single primary click opens the Quick Panel when hidden;
- another single click hides it;
- double click opens or restores the full application;
- right click keeps the existing tray context menu;
- opening the full application replaces the compact content;
- the compact and full interfaces are never shown simultaneously.

On Windows, the single-click action is delayed until the configured
double-click interval expires. A second click cancels the pending compact
action and opens the full application, avoiding a visible compact-window
flash.

The controller saves full-window dimensions before entering compact mode and
restores them when returning to the application. Compact positioning near the
tray remains best-effort:

- Windows can use the available native/Flet window information;
- X11 window managers generally allow equivalent positioning;
- Wayland compositors may choose the final position.

## Linux strategy

The feature uses the same `QuickPanelController` and `QuickPanelView` on all
platforms. No distro-specific UI implementation or new Linux-only dependency
is planned.

`pystray` behavior varies by backend:

- Windows, GTK, and X11 backends can use a default primary action when
  available;
- AppIndicator environments, common on Wayland and several desktop shells,
  do not consistently expose the same primary-click callback.

For AppIndicator/Wayland, the context menu provides explicit Quick Panel and
full-app actions. This keeps the feature usable across Ubuntu, Debian, Fedora,
Arch-based distributions, and other desktops supported by the installed tray
backend.

## State and data flow

When the Quick Panel opens:

1. the controller reads `get_target_config()`, `get_bulbs_detailed()`, and
   `get_tray_status()`;
2. the view renders the active light, target mode, online state, current power,
   brightness, RGB, and Kelvin values when available;
3. Color Studio synchronizes the active device state without emitting a
   command;
4. favorites are loaded from the existing manager.

For a user action:

1. the view emits an intent to `QuickPanelController`;
2. the controller updates targeting when needed;
3. power or favorite actions run through `ActionSequenceExecutor`;
4. Color Studio uses its existing calibrated application path;
5. the controller requests a fresh state snapshot and refreshes the view.

Offline or partially reachable targets remain visible with their status. A
failed command must not optimistically overwrite the last confirmed device
state.

## Planned files

The implementation is expected to create or modify:

- `core/quick_panel_controller.py`;
- `ui/quick_panel_view.py`;
- `core/background/tray_service.py`;
- `main.py`;
- `tests/test_quick_panel.py`;
- this document.

The list must be updated after implementation if the final file set differs.

## Test strategy

Development follows test-first increments in `tests/test_quick_panel.py`.
Tests cover:

- controller and view construction;
- state snapshots;
- individual and all-light targeting;
- ON and OFF action routing;
- RGB, White, Scene, and Brightness favorites;
- one-window quick/hidden/full transitions;
- tray callback integration;
- Windows single/double-click arbitration;
- Linux visible-menu fallback;
- exact reuse of the existing Color Studio layout.

Existing Color Studio and tray tests remain regression coverage. Final
validation must run:

```text
python -m compileall -q main.py app_meta.py core config ui localization tests tools
python -m pytest -q
python tools/i18n_audit.py
git diff --check
```

## Decisions

- Adopt the Focused stack visual design.
- Place quick colors below the calibrated Color Studio picker.
- Preserve Color Studio as the only RGB picker.
- Use one native window and switch its content and geometry.
- Keep the current right-click tray menu.
- Treat group mode as all available lights.
- Use an explicit AppIndicator/Wayland menu fallback.
- Route all visible copy through existing i18n.
- Keep protected services, persistence, and protocol untouched.
- Avoid new platform-specific dependencies in this foundation.

## Risks

- Flet window geometry and focus behavior vary between Windows, X11, and
  Wayland.
- `pystray` AppIndicator does not provide the same primary-click behavior as
  Windows/X11; the explicit menu entry is the required fallback.
- Deferring a Windows single click introduces a delay equal to the system
  double-click interval.
- Group mode cannot represent a user-selected subset without a future,
  separately approved `LightController` change.
- Mounting the full existing Color Studio responsive layout prioritizes
  correctness over perfect compact spacing in this foundation.
- Automated tests cannot verify actual WiZ color reproduction, native tray
  behavior on every desktop environment, or real multi-monitor placement.

## Implementation record

### Files

- `core/quick_panel_controller.py` adds snapshot creation, existing-service
  action routing, live-state updates, and full/quick/hidden transitions for the
  shared native window.
- `ui/quick_panel_view.py` adds the localized Focused-stack view and mounts the
  existing `ColorPanel.main_layout` without reconstructing or modifying the
  calibrated picker.
- `core/background/tray_service.py` adds optional Quick Panel and full-app
  callbacks, Windows single/double-click arbitration, and localized visible
  menu actions for Linux/AppIndicator fallback.
- `main.py` composes one shared content host, one controller, and one compact
  view around the existing `Page`, `LightController`, and `WizzApp`. Each WiZ
  state update is fanned out to both interfaces.
- `tests/test_quick_panel.py` covers snapshots, live state, devices, individual
  and all-light targeting, ON/OFF, RGB/White/Scene/Brightness favorites,
  localization changes, one-window transitions, tray callbacks, Windows click
  arbitration, Linux primary action, and the visible menu fallback.
- `docs/codex/quick-panel-design.md` records the approved architecture and this
  implementation.

No protected module, WiZ protocol implementation, favorite contract or JSON
format, Color Studio internal, or localization implementation/catalog was
changed. All required Quick Panel labels were already present in both existing
catalogs, so no new keys were necessary.

### Implemented flow

`TrayService` schedules compact/full intents on the existing Flet session.
`QuickPanelController` swaps only the content of the shared host and adjusts or
restores the same native window geometry. `QuickPanelView` reads detached
snapshots from the shared `LightController` and `FavoritesManager`; commands
continue through the existing target APIs and `ActionSequenceExecutor`.

Windows defers a primary click for the operating-system double-click interval.
Timer completion toggles the compact panel; a second click cancels that timer
and restores the full app without first flashing the compact content.
Non-Windows backends use the compact action as their default when supported,
while explicit Quick Panel and full-app menu entries keep AppIndicator and
Wayland environments usable.

### Validation

- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`
  completed successfully.
- `python -m pytest -q` completed with `212 passed`; the 98 warnings are
  pre-existing Flet `ElevatedButton` deprecations in unrelated panels.
- `python tools/i18n_audit.py` reported `579` matching English/Spanish keys and
  zero potential hardcoded UI strings.
- Focused Quick Panel, Color Studio, tray, main activation, and state-dispatch
  regression suites passed.
- A controlled `python main.py` smoke remained healthy for eight seconds:
  Flet created one session, hotkeys initialized, the tray started, the app
  reached its ready state, and discovery ran. The exact Python and Flet
  processes created for the smoke were then stopped.

### Decisions and deviations

The implementation follows the approved foundation without architectural
deviations. It deliberately mounts the complete responsive Color Studio layout
instead of creating a compact picker variant. Group mode remains the existing
all-lights target because a custom subset would require a separately approved
controller contract.

Review hardening preserves maximized/full-screen state and current responsive
viewport geometry, remounts Color Studio after its language-driven rebuild,
reloads favorites from the existing manager when snapshots are requested,
avoids compact rendering work while the full app is active, and refuses to
mutate Flet controls from the tray thread after an exposed session loop stops.

### Remaining risks and next steps

- Verify actual tray primary-click behavior on Windows, X11, and representative
  AppIndicator/Wayland desktops.
- Manually exercise Quick Panel open/hide, double-click full restore, and the
  right-click menu; the non-interactive smoke cannot validate pointer gestures.
- Verify compact positioning and focus on multiple monitors; compositors may
  override requested placement.
- Exercise RGB accuracy, Kelvin ranges, power, favorites, and multi-device
  targeting with physical WiZ lights.
- Refine compact spacing only through composition that leaves the protected
  Color Studio component unchanged.

## Premium UI redesign implementation record

### Task 1 checkpoint: compact Color Studio adapter

Status: completed.

Files changed:

- `ui/components/quick_color_studio_adapter.py` adds a compact composition
  boundary around a Quick-Panel-only `ColorPanel` instance.
- `tests/test_quick_panel.py` covers compact Color composition, full removal of
  the mounted RGB tree in White mode, and remounting after Color Studio rebuilds
  its controls for a language change.
- `docs/codex/queries/2026-07-25-03-quick-panel-ui-review.md` records the
  approved redesign plan and continuity context.

The adapter mounts the existing Color/Precise or White subtree, followed by the
existing brightness and manual-apply controls. It never mounts
`ColorPanel.main_layout`, never duplicates picker or conversion logic, and
keeps one active Flet parent for every mounted Color Studio control.

Checkpoint validation:

- `python -m pytest -q tests/test_quick_panel.py tests/test_color_panel_studio.py`
  completed with `51 passed`.

### Task 2 checkpoint: premium card shell

Status: completed.

Files changed:

- `ui/quick_panel_view.py` replaces the reduced desktop-style stack with a
  five-card overlay shell: header/device, power, target, compact Color Studio,
  and quick favorites.
- `tests/test_quick_panel.py` covers the absence of desktop navigation, active
  device/status rendering, card structure, six-favorite limit, “View all”
  navigation, and existing action callbacks.

The header uses localized product/status/settings copy and preserves user
device names. ON/OFF actions are permanently visible and enlarged. Favorites
are rendered as a two-row compact card grid instead of a text list. The
existing adapter receives viewport, live state, and language updates.

Checkpoint validation:

- `python -m pytest -q tests/test_quick_panel.py tests/test_full_app_i18n.py tests/test_home_color_i18n.py`
  completed with `42 passed`; the 98 warnings are pre-existing Flet
  `ElevatedButton` deprecations outside the Quick Panel.

### Task 3 checkpoint: premium overlay behavior

Status: completed.

Files changed:

- `core/quick_panel_controller.py` adds fixed overlay geometry, bottom-right
  work-area positioning, compact window chrome, complete window-property
  restoration, and full-app section navigation.
- `ui/components/quick_color_studio_adapter.py` follows Color Studio's
  externally synchronized RGB/White mode so the mounted compact tree always
  matches the current light state.
- `tests/test_quick_panel.py` covers overlay sizing and chrome, deterministic
  positioning, full restoration, section navigation, and state-driven White
  composition.

Quick mode now uses a 440 x 680 non-resizable, always-on-top window positioned
16 px from the bottom-right of the Windows work area under the tray cursor,
with a primary-monitor fallback. The controller captures every property it
changes and restores the full app before navigating to Favorites or Settings.
Platforms that do not expose a work area keep best-effort compositor placement
while retaining the existing tray actions.

Checkpoint validation:

- `python -m pytest -q tests/test_quick_panel.py tests/test_color_panel_studio.py tests/test_tray_window_restore.py tests/test_tray_branding.py tests/test_full_app_i18n.py tests/test_home_color_i18n.py`
  completed with `81 passed`; the 98 warnings are pre-existing Flet
  `ElevatedButton` deprecations outside the Quick Panel.

### Task 4 checkpoint: review hardening and final validation

Status: completed.

Final architecture and UX:

- `QuickPanelView` uses Header, Power, Target, Color Studio, and Favorites card
  order, with the real WizZ icon and no desktop navigation.
- `ColorStudioQuickAdapter` separates passive composition from behavioral mode
  changes. Construction, i18n rebuilds, and external state synchronization
  never dispatch lighting actions; only an explicit Color/White click delegates
  to Color Studio's selector.
- Existing White and Precise views survive adapter construction. White removes
  the mounted RGB subtree, and external Kelvin/RGB state remounts the matching
  compact content.
- Windows placement selects the monitor under the tray cursor and restores
  every changed native window property when returning to the full app.

Review problems and solutions:

- Independent review found that initializing a saved White mode through
  Color Studio's behavioral selector could emit an unintended live Kelvin
  command. A passive `_mount_mode` path and no-dispatch regressions removed the
  startup side effect.
- The original Windows provider returned only the primary monitor work area.
  It now uses `GetCursorPos`, `MonitorFromPoint`, and `GetMonitorInfoW`, with
  `SPI_GETWORKAREA` retained as a safe fallback.
- The i18n audit found one decorative hardcoded separator. Removing it left all
  visible Quick Panel framework copy on the existing ES/EN catalogs.

Final validation:

- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`
  completed successfully.
- `python -m pytest -q` completed with `227 passed`; the 98 warnings are
  pre-existing Flet `ElevatedButton` deprecations in unrelated panels.
- `python tools/i18n_audit.py` reported `579` matching English/Spanish keys and
  zero potential hardcoded UI strings.
- The final related regression group completed with `84 passed`; the same 98
  unrelated warnings were present.
- `git diff --check` completed successfully.
- `python main.py` confirmed the existing single-instance process was restored
  and no second app instance was created.

Remaining manual risks:

- Close the already-running pre-redesign process before visually testing this
  commit's rendered tray overlay.
- Verify frameless focus, left-click toggle, double-click full restore,
  Color/White remounting, favorites, and ON/OFF with pointer input and physical
  lights.
- Verify cursor-monitor placement on mixed-DPI Windows systems and compositor
  behavior on X11/AppIndicator/Wayland desktops.
