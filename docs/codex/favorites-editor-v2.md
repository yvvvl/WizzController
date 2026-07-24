# Favorites editor v2

## Current state found

The repository is on `feature/v1.1.0-favorites-editor-v2` at commit `820c8e5`.
The working tree already contains six intentional deletions under
`wizz_phase55_routines_visual_editor/`; they belong to an obsolete
implementation folder and must be preserved without including them in the
Favorites v2 commit.

Before v2, `FavoritesPanel` contained four named builder methods, but the real
dialog still owned one universal state dictionary with RGB, White, Scene, and
Brightness fields together. Its preview and type transition were nested
closures. Existing tests called `_render_editor_mode()` directly, so they
verified the builders in isolation but did not prove that changing the real
dropdown destroyed the mounted RGB tree and refreshed the preview.

## Why the previous implementation failed

The previous implementation separated control construction but not the complete
editor lifecycle:

- all modes share a universal mutable state dictionary;
- preview controls and update logic are nested inside `_favorite_dialog()`;
- mode tests bypass the real dropdown callback;
- incompatible state is retained when the type changes;
- the mounted-dialog transition is therefore not covered by tests.

The runtime path is `WizzApp.panels[3]`, which directly instantiates this
`FavoritesPanel`; there is no duplicate panel implementation. The installed
Flet version defines the material Dropdown selection event as `on_select`.
The previous dialog dynamically assigned `kind.on_change`, and the Scene
selector did the same. That attribute is not the serialized Dropdown event, so
the real app never calls the type transition even though direct unit tests pass.
The initial RGB tree consequently remains mounted after choosing White, Scene,
or Brightness.

## Files inspected

- The new specification attachment
- Current branch, status, log, and existing diff

- `ui/components/favorites_panel.py`
- `ui/color_studio.py`
- `ui/components/color_panel.py`
- `ui/components/scenes_panel.py`
- `ui/scene_visuals.py`
- `config/favorites_manager.py`
- `config/custom_scenes_manager.py`
- `core/wiz_scenes.py`
- `ui/app.py` for the real panel mounting path
- related tests

Inspection confirmed all of the above files and the current implementation
diff from commit `820c8e5`.

## New architecture

- One active mode state exists at a time. Its keys are capability-specific:
  RGB has RGB/Hue/Purity, White has Kelvin/Brightness, Scene has scene
  selection/speed, and Brightness has only its percentage.
- independent `_build_rgb_editor()`, `_build_white_editor()`,
  `_build_scene_editor()`, and `_build_brightness_editor()` return unrelated
  control trees with callbacks closed over only their own state.
- `_FavoriteEditorSession` owns the mounted type selector, editor host, preview,
  summary, and current mode state.
- `_switch_editor_session()` discards the prior state and root, creates a fresh
  mode state and tree, recalculates preview, and updates mounted controls.
- `_update_preview_from_state()` is the only preview dispatcher and replaces
  the icon and all metadata on every update.
- Both the favorite type Dropdown and the Scene Dropdown use Flet's registered
  `on_select` event.
- Static Scene selections contain no speed controls. Selecting a dynamic scene
  rebuilds the Scene selection subtree and adds a newly created speed slider;
  no controls use `visible=False`.
- Integration tests invoke the exact `on_select` callback used by the dialog.

## Decisions

- Preserve the current Favorites JSON contract exactly.
- Do not modify `FavoritesManager`, files under `core/`, or the intentional
  deletions.
- Continue reusing the calibrated Color Studio utilities for RGB.
- Stage only v2-related files at commit time.
- Preserve White brightness as editor/preview state only because the mandated
  White persistence contract remains the Kelvin integer.
- Keep only custom scenes whose mode can map to the existing RGB, White, or
  Scene favorite contracts.

## Files changed

- `ui/components/favorites_panel.py`
- `tests/test_favorites_editor_v2.py`
- `tests/test_favorites_editor_modes.py` (updated the static-scene assertion to
  require an absent speed subtree instead of a hidden one)
- `docs/codex/favorites-editor-v2.md`

## Risks

- White brightness cannot be persisted in the current Kelvin-only favorite
  contract. It can remain independent editor/preview state, but extending the
  stored value would require stopping and expanding the authorized scope.
- A native Flet dialog is harder to exercise than a standalone control tree;
  tests need a small testable dialog/editor controller surface.
- Manual validation requires launching the desktop app and visually exercising
  the mounted dropdown transitions.
- Automated tests and the startup smoke cannot confirm real WiZ hardware
  behavior or visual layout on the user's display.

## Tests

- Focused editor suites:
  `python -m pytest -q tests/test_favorites_editor_v2.py
  tests/test_favorites_editor_modes.py tests/test_favorites_i18n.py`
  - Passed: 24 tests.
- Full compile:
  `python -m compileall -q main.py app_meta.py core config ui localization
  tests tools`
  - Passed.
- Full suite: `python -m pytest -q`
  - Passed: 190 tests.
  - 98 pre-existing Flet `ElevatedButton` deprecation warnings remain in
    unrelated panels.
- Localization audit: `python tools/i18n_audit.py`
  - Passed: 579 matching en/es keys and zero potential hardcoded UI strings.
- `git diff --check`
  - Passed.
- `python main.py`
  - Startup smoke passed: the process remained healthy for eight seconds.
  - The process and its Flet desktop child were closed after the check.
  - Visual interaction and testing with a real WiZ device remain pending.

## Commands executed

- `git branch --show-current`
- `git status --short`
- `git log -3 --oneline`
- `git diff --name-status`
- `git diff --stat`
- `git diff -- wizz_phase55_routines_visual_editor/core/action_sequence.py`
- `rg` / `Get-Content` inspection of all required source files and tests
- `python -m pytest -q tests/test_favorites_editor_v2.py
  tests/test_favorites_editor_modes.py tests/test_favorites_i18n.py`
- `python -m compileall -q main.py app_meta.py core config ui localization
  tests tools`
- `python -m pytest -q`
- `python tools/i18n_audit.py`
- `git diff --check`
- `python main.py` through a controlled eight-second process smoke
