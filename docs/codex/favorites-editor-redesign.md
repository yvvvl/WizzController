# Favorites editor redesign

## Objective

Replace the single RGB-oriented Favorites editor with capability-specific
editors for RGB, White, Scene, and Brightness. Changing the favorite type must
replace the complete editor subtree so controls, callbacks, icons, and preview
state from the previous mode cannot leak into the new mode.

## Problem found

`FavoritesPanel._favorite_dialog()` owned one large nested editor function.
Although it cleared the visible control list, all modes shared RGB-derived
state and a generic preview. White used a percentage-to-Kelvin approximation
instead of a real Kelvin control, Scene only exposed built-in WiZ scenes, and
Brightness inherited the same generic dialog identity.

The RGB implementation also duplicated standard HSV conversion with
`colorsys`; it did not use the calibrated Hue/Purity pipeline already used by
Color Studio.

## Files inspected

- `ui/components/favorites_panel.py`
- `ui/components/color_panel.py`
- `ui/color_studio.py`
- `ui/components/scenes_panel.py`
- `ui/scene_visuals.py`
- `config/favorites_manager.py`
- `config/custom_scenes_manager.py`
- `core/light_controller.py` (read-only compatibility check)
- `core/action_sequence.py` (read-only compatibility check)
- `core/wiz_scenes.py`
- `localization/catalogs/es.py`
- `localization/catalogs/en.py`
- `tests/test_favorites_i18n.py`
- `tests/test_full_app_i18n.py`
- `tests/test_color_studio.py`
- `tests/test_color_panel_studio.py`

## Architecture before the change

The dialog created all mode controls inside one nested `render_editor()`
closure. RGB, White, Scene, and Brightness shared a broad mutable dictionary.
The RGB branch used local HEX/HSV helpers, while the remaining branches
manually changed a generic preview.

Favorite persistence and application use the existing stable contract:

- RGB: HEX string
- White: Kelvin integer
- Scene: `{sceneId, speed}`
- Brightness: percentage integer

## Architecture after the change

The panel owns a small editor dispatcher and four independent builders:

- `_build_rgb_editor()`
- `_build_white_editor()`
- `_build_scene_editor()`
- `_build_brightness_editor()`

The dispatcher assigns a newly built control list on every mode transition.
Each builder creates only its own controls and callbacks. Shared helpers
calculate preview metadata and convert a selected custom scene into one of the
existing favorite payloads.

RGB imports Color Studio's calibrated palette geometry, Hue/Purity conversion,
HEX parsing, HSV conversion, and palette image. White works directly in the
device Kelvin range and has a separate brightness state. Scene combines WiZ
and compatible custom-scene choices and only exposes speed for dynamic scenes.
Brightness has a dedicated minimal editor and preview.

## Decisions

- Keep `FavoritesManager`, `LightController`, `ActionSequenceExecutor`, and the
  JSON contract unchanged.
- Reuse `ui.color_studio` as the source of truth for RGB and Kelvin conversion.
- Treat the White brightness control as independent dialog state. The stable
  White favorite payload remains a Kelvin integer because changing it would
  break existing consumers that are explicitly outside this task's scope.
- Resolve a selected custom scene to its compatible persisted favorite type:
  RGB custom scenes become RGB favorites, White custom scenes become White
  favorites, and WiZ-based custom scenes become Scene favorites. Combo custom
  scenes are excluded because the favorite contract cannot represent them.
- Always derive the saved icon from the final mode so an icon from the
  previously selected type cannot survive a type change.

## Problems encountered

The existing White favorite format has no brightness field, and the existing
favorite types have no custom-scene identifier. Supporting either as a new
persistent shape would require changes to protected modules and multiple
favorite consumers. The editor therefore preserves the stable contract and
adapts compatible custom scenes at save time.

## Files modified

- `ui/components/favorites_panel.py`
- `localization/catalogs/en.py`
- `localization/catalogs/es.py`
- `tests/test_favorites_editor_modes.py`
- `tests/test_favorites_i18n.py`
- `docs/codex/favorites-editor-redesign.md`

## Tests executed

- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`
  - Passed.
- `python -m pytest -q`
  - Passed: 180 tests.
  - Existing Flet `ElevatedButton` deprecation warnings remain in Scenes,
    Routines, and Hotkeys; they are outside this task.
- `python tools/i18n_audit.py`
  - Passed: 579 matching en/es keys and zero potential hardcoded UI strings.
- `git diff --check`
  - Passed.

## Commands used

- `git branch --show-current`
- `git status --short`
- `git log -2 --oneline`
- `rg` and `Get-Content` for scoped source inspection
- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`
- `python -m pytest -q tests/test_favorites_editor_modes.py tests/test_favorites_i18n.py`
- `python -m pytest -q`
- `python tools/i18n_audit.py`
- `git diff --check`
- `git diff --stat`
- `git diff --name-only`

## Pending risks

- White brightness is visible and independently editable in the dialog but is
  not persisted in the legacy Kelvin-only favorite payload.
- Custom combo scenes cannot be represented without extending the favorite
  type contract and are not offered in this editor.
- GUI behavior still requires the manual checklist on a Windows desktop with
  an available WiZ device.

## Next steps

Run the manual checklist with a real device, including immediate RGB preview,
Kelvin and brightness changes, dynamic/static scene speed, type transitions,
and Spanish/English switching. A future version may extend the favorite
contract to persist White brightness and custom-scene identity, but that work
must update every favorite consumer together.
