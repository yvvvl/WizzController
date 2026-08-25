# Query 2026-07-25-03: Quick Panel Premium UI redesign

Status: Completed

> **Execution:** Inline, incremental TDD on the existing
> `feature/v1.2.0-quick-panel-design` branch. No new branch, worktree, merge, or
> push.

## Goal

Transform the validated Quick Panel foundation into a compact, card-based,
professional lighting overlay while preserving one Flet `Page`, one
`LightController`, the existing tray lifecycle, favorites contract, and Color
Studio calibration.

## Starting state

- Branch: `feature/v1.2.0-quick-panel-design`
- Base commit: `ea1cc0e` (`feat: add WizZ Quick Panel foundation`)
- Related baseline: 56 tests passed in
  `tests/test_quick_panel.py`, `tests/test_color_panel_studio.py`, and
  `tests/test_tray_window_restore.py`.
- Existing untracked `docs/codex/plans/` content belongs to an earlier session
  and is outside this query.

## Architecture

`QuickPanelView` becomes a compact overlay shell made from independent cards:
header/device, power, target, active Color Studio mode, and favorites.

A new `ColorStudioQuickAdapter` owns one Quick-Panel-only `ColorPanel`
instance. It mounts only the active compact subtree:

```text
Color mode
  existing color_section
  existing precise_section (only when Color Studio activates it)
  existing brightness_card
  existing apply controls

White mode
  existing white_section
  existing brightness_card
  existing apply controls
```

The full desktop app keeps its separate existing `ColorPanel`. The adapter
never mounts one live control in two active parents and never copies picker,
conversion, calibration, Kelvin, brightness, throttling, or edit-guard logic.

`QuickPanelController` remains the window-mode coordinator. Quick mode will use
a fixed 440 × 680 window, overlay chrome, always-on-top behavior, and
best-effort bottom-right positioning. It will capture and restore every window
property it changes.

## Global constraints

- Do not modify `core/light_controller.py`, WiZ protocol code,
  `config/favorites_manager.py`, favorite JSON, `core/action_sequence.py`,
  `ui/color_studio.py`, or `ui/components/color_panel.py`.
- Use the existing localization manager for all visible copy.
- Reuse existing ES/EN keys when available; add matching catalog entries only
  if a genuinely new label is required.
- Keep `ActionSequenceExecutor`, `FavoritesManager`, and `TrayService`.
- Keep only `Individual` and `All lights`.
- Show at most six quick favorites.
- Preserve left-click Quick Panel, right-click menu, and double-click full app.
- Produce one final commit: `feat: redesign WizZ Quick Panel UI`.

## Incremental implementation plan

### Task 1: Compact Color Studio adapter

**Files**

- Create `ui/components/quick_color_studio_adapter.py`.
- Modify `tests/test_quick_panel.py`.
- Update the premium checkpoint in
  `docs/codex/plans/2026-07-25-wizz-quick-panel-design.md`.

**TDD cycle**

1. Add a test proving the adapter exposes exactly Color and White selectors,
   starts with the existing RGB section before brightness, and does not mount
   `ColorPanel.main_layout`.
2. Run the focused test and verify failure because the adapter does not exist.
3. Implement `ColorStudioQuickAdapter` with an injected `ColorPanel` for
   deterministic tests.
4. Add a test proving White mode replaces the content host with only the
   existing White subtree, leaving no RGB/quick-color subtree in the mounted
   mode tree.
5. Implement `set_mode("color" | "white")`, delegate mode state to Color
   Studio, and rebuild only the adapter tree.
6. Add a language-rebuild test proving new Color Studio controls are remounted.
7. Run `tests/test_quick_panel.py` and `tests/test_color_panel_studio.py`.

### Task 2: Premium card shell and favorites

**Files**

- Modify `ui/quick_panel_view.py`.
- Modify `tests/test_quick_panel.py`.
- Update the premium checkpoint in
  `docs/codex/plans/2026-07-25-wizz-quick-panel-design.md`.

**TDD cycle**

1. Add a test proving the root contains card sections and no
   `NavigationRail`.
2. Add a test proving the header renders localized product/status copy and the
   active device name from the snapshot.
3. Add a test proving favorites are rendered as compact cards, capped at six,
   and keep their existing execution callbacks.
4. Add a test proving localized “View all” opens the full app at Favorites.
5. Implement the compact card hierarchy with a 14 px outer gutter, restrained
   card spacing, large ON/OFF actions, and a two-option target selector.
6. Keep user device/favorite names unchanged and resolve all framework copy
   through i18n.
7. Run `tests/test_quick_panel.py` and the full-app i18n regression tests.

### Task 3: Overlay window behavior

**Files**

- Modify `core/quick_panel_controller.py`.
- Modify `tests/test_quick_panel.py`.
- Update the premium checkpoint in
  `docs/codex/plans/2026-07-25-wizz-quick-panel-design.md`.

**TDD cycle**

1. Add a failing test for 440 × 680 fixed size, frameless/title-bar-hidden
   chrome, shadow, and always-on-top state.
2. Add a failing test for a deterministic work-area provider that positions
   the panel 16 px from the bottom-right corner.
3. Add a failing test proving full mode restores size, position, chrome,
   always-on-top, and responsive viewport.
4. Add a failing test for opening Favorites and Settings in the full app
   through `WizzApp.navigate_to(3|5)`.
5. Implement the minimal property capture, positioning provider, and full-view
   navigation.
6. Run Quick Panel and tray regression tests.

### Task 4: Final documentation and validation

**Files**

- Update `docs/codex/plans/2026-07-25-wizz-quick-panel-design.md` with the final Premium UI
  Implementation record.
- Complete this query report without modifying earlier reports.

**Validation**

1. Run:

   `python -m compileall -q main.py app_meta.py core config ui localization tests tools`

2. Run:

   `python -m pytest -q`

3. Run:

   `python tools/i18n_audit.py`

4. Run:

   `git diff --check`

5. Start `python main.py` from this checkout and document exactly which
   automated startup signals and manual interactions were verified.
6. Show `git status`, `git diff --stat`, and `git diff --check`.
7. Stage only approved files and commit with
   `feat: redesign WizZ Quick Panel UI`.
8. Stop without merge or push.

## Initial decisions

- Use a dedicated adapter rather than the complete
  `ColorPanel.main_layout`; this solves the oversized desktop layout without
  creating a second color implementation.
- Keep precise HEX/RGB controls inside Color mode. The top-level selector still
  contains only Color and White.
- Preserve manual-apply behavior through existing Color Studio apply controls;
  hiding them would break users who disabled live apply.
- Use the work area of the Windows monitor under the tray cursor and
  best-effort unchanged positioning elsewhere; Wayland may override
  coordinates.
- Use existing localization keys; no catalog edit is planned unless tests
  expose missing copy.

## Continuity record

### 1. Current implementation state

The premium Quick Panel redesign is implemented on
`feature/v1.2.0-quick-panel-design` on top of `ea1cc0e`. The existing
single-window foundation remains intact: tray actions switch the shared Flet
content host between the full app and Quick Panel without creating a second
`Page` or `LightController`.

The compact UI is a fixed 440 x 680 overlay with five vertically ordered
cards: header/device, power, target, Color Studio, and favorites. It uses the
real WizZ asset, large ON/OFF actions, a two-mode target selector, and up to
six quick-favorite cards.

### 2. Phase objective and result

The goal was to replace the reduced-desktop appearance with a daily-use
lighting control surface inspired by native quick settings. The result removes
desktop navigation, establishes a clear card hierarchy, keeps power near the
top, composes only the active Color Studio subtree, and restores the full
application exactly when the user leaves compact mode.

### 3. Final architecture

Components and responsibilities:

- `TrayService` keeps ownership of left-click, right-click, and double-click
  intent handling.
- `QuickPanelController` owns compact/full/hidden window modes, detached
  snapshots, existing command dispatch, overlay geometry, and full-section
  navigation.
- `QuickPanelView` owns only the premium card composition and maps detached
  snapshot data into visual controls.
- `ColorStudioQuickAdapter` is the compact composition boundary. It owns no
  color math or protocol behavior and mounts either the existing Color/Precise
  subtree or the existing White subtree, followed by existing brightness and
  manual-apply controls.
- The existing Quick-Panel-only `ColorPanel` instance continues to own palette
  calibration, RGB/HEX behavior, Kelvin ranges, presets, throttling, local edit
  guards, and brightness.

Data and action flow:

```text
TrayService
  -> QuickPanelController.open_quick()/toggle_quick()/open_full()
  -> shared Flet content host
  -> QuickPanelView.update_snapshot()
  -> ColorStudioQuickAdapter.sync_state()
  -> existing ColorPanel behavior

Quick Panel action
  -> QuickPanelController
  -> ActionSequenceExecutor or existing LightController target API
  -> WiZ light(s)
```

### 4. Complete file list

- `core/quick_panel_controller.py`: fixed 440 x 680 overlay constants;
  cursor-monitor work-area positioning; window chrome capture/restore;
  full-section navigation.
- `ui/quick_panel_view.py`: premium card shell, real WizZ icon, active-device
  status, large power actions, compact target controls, favorite card grid,
  View all, and settings navigation.
- `ui/components/quick_color_studio_adapter.py`: compact Color/White
  composition using existing Color Studio controls and behavior.
- `tests/test_quick_panel.py`: adapter, visual hierarchy, icon, favorite
  limit, i18n, callbacks, overlay geometry, restoration, navigation, and
  state-driven mode regression coverage.
- `docs/codex/plans/2026-07-25-wizz-quick-panel-design.md`: incremental and final implementation
  record.
- `docs/codex/queries/2026-07-25-03-quick-panel-ui-review.md`: this standalone
  continuity report.

No protected module, favorite JSON contract, WiZ protocol code, color
conversion, Color Studio implementation, or localization catalog was changed.

### 5. Technical and UX decisions

- A dedicated adapter was selected instead of mounting
  `ColorPanel.main_layout`, because the desktop layout was the principal source
  of excess size. Copying picker/conversion logic was rejected.
- The adapter mounts one active subtree at a time. White mode has no mounted
  RGB palette or quick-color subtree; returning to Color remounts the current
  Color Studio controls.
- Precise HEX/RGB remains reachable from the existing Color content rather
  than becoming a third large top-level mode.
- The real `icon.png` asset is used in the header; user-supplied device and
  favorite names are left unchanged.
- Existing i18n keys cover all framework copy, so adding catalog keys or a
  parallel localization mechanism was unnecessary.
- A Windows work-area provider positions the overlay 16 px from the
  bottom-right. Other compositors retain best-effort placement because forcing
  coordinates is not portable, especially on Wayland.
- Every native window property changed for compact mode is captured and
  restored. Full content is restored before navigation to Favorites or
  Settings.

Problems found and resolved:

- Reusing the complete responsive Color Studio preserved behavior but kept the
  desktop visual weight. The compact adapter now composes only the necessary
  existing subtrees.
- Color Studio rebuilds its controls when language changes. The adapter
  remounts the rebuilt controls instead of retaining stale Flet instances.
- External Kelvin state could update Color Studio to White while the adapter
  still displayed Color. State synchronization now remounts White as part of
  the same update.
- An existing White preference could be overwritten during adapter creation.
  Initial composition now follows Color Studio's current `view_mode` without
  invoking its behavioral selector or dispatching a light action.
- Independent review found the primary-monitor-only placement fallback. The
  provider now resolves the work area for the monitor under the tray cursor
  before falling back to the primary monitor.
- The i18n audit identified a decorative hardcoded separator. It was removed;
  the final audit has no potential visible hardcoded string.

### 6. Service integrations

- **TrayService:** unchanged; its existing primary action, menu fallback, and
  double-click arbitration call the same controller entry points.
- **QuickPanelController:** remains the sole compact/full window coordinator
  and adds no lighting behavior.
- **QuickPanelView:** receives detached snapshots and never reads or writes
  favorite JSON directly.
- **LightController:** the one shared instance remains responsible for
  selection, single/all targeting, device status, and WiZ operations.
- **ActionSequenceExecutor:** still executes ON, OFF, and favorites using
  existing action payloads.
- **FavoritesManager:** still supplies the existing favorites contract; the
  view renders no more than six and delegates execution by ID.
- **Color Studio:** a dedicated Quick-Panel `ColorPanel` owns all color/white
  behavior. The adapter only changes composition and never creates a picker.
- **i18n:** all framework labels come from the existing localization manager;
  both English and Spanish continue to use the same keys.

### 7. Test and validation state

- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`
  -> completed successfully.
- `python -m pytest -q`
  -> `227 passed`, with 98 pre-existing Flet `ElevatedButton` deprecation
  warnings in unrelated panels.
- `python tools/i18n_audit.py`
  -> `579` matching EN/ES keys and `0` potential hardcoded UI strings.
- `git diff --check`
  -> completed successfully.
- Related Quick Panel, Color Studio, tray, and i18n regressions
  -> `84 passed`; the same 98 unrelated warnings were present.

Focused development checkpoints used strict red/green cycles for compact
composition, White tree replacement, premium hierarchy, favorite limits,
overlay geometry, restoration, and full-section navigation.

### 8. Manual state and limitations

Running `python main.py` from this checkout reached the single-instance guard,
which detected and restored the already-running WizZ Desktop process. It exited
cleanly without creating a second application instance. Because that process
had loaded code before this redesign and this environment has no desktop
pointer-control channel, the following physical interactions are not claimed
as manually verified:

- left-click tray placement and toggle;
- live Color <-> White transitions in the rendered desktop client;
- physical ON/OFF and favorite execution;
- double-click full-window restore;
- multi-monitor and Linux compositor placement.

These paths are covered by automated state/callback tests, but a human smoke
with the existing app fully closed is still required before release.

### 9. Recommended next steps

1. Close every running WizZ instance, start this commit, and execute the seven
   manual checks from the approved specification.
2. Verify pointer behavior on Windows, X11, and representative
   AppIndicator/Wayland environments.
3. Exercise Color/White accuracy, real Kelvin limits, brightness, favorites,
   and single/all targeting with physical WiZ lights.
4. Check cursor-monitor bottom-right placement on mixed-DPI and multi-monitor
   Windows setups.
5. Keep future visual refinements inside `QuickPanelView` or the adapter; do
   not fork protected Color Studio or controller logic.
