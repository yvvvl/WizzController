# Qt UI parity audit

Source of truth: the mature Flet panels under `ui/components/` and the accepted WiZ-style color picker reference.

## Shared shell

- Done: frameless window, sidebar, theme tokens, page transitions, expansive press feedback, wheel/trackpad scrolling, dynamic content heights, native QA screenshots.
- Partial: responsive breakpoints and reduced-motion preference.
- Missing: tray lifecycle, updater surfaces, localization wiring and persisted window geometry.

## Home

- Done: light cards, target selection, master power, live brightness, quick actions and favorite shortcuts.
- Missing: device refresh feedback, offline/error states, richer target selector and parity with every Flet status state.

## Color Studio

- Done: WiZ RGB picker, CCT picker, continuous sampled transport, live brightness, correct RGB/white mode, save current, recent values and quick favorites.
- Missing: precise HEX/RGB/HSV editor, persisted history, live/apply mode switch and detected device temperature range.

## Scenes

- Done: grouped WiZ catalog, selected-scene feedback, continuously sampled speed, save-current flow and custom scene create/edit/delete for RGB, white and WiZ modes.
- Missing: combo/multi-action scene editor, richer icon selection and translated catalog names.

## Favorites

- Done: dedicated responsive card grid, apply, create, edit and confirmed delete; persisted RGB, white, brightness and WiZ-scene values; reusable modal editor.
- Missing: visual spectrum/CCT controls inside the modal and drag reordering.

## Routines

- Done: list and execute existing routines.
- Missing: create/edit/duplicate/delete, ordered action editor, delays, conditions, targets and capture-current-state flow.

## Settings

- Done: theme selection.
- Missing: discovery, add-by-IP, destination selection, slider cadence, language, reduced motion, tray/startup settings and updater controls.

## Hotkeys

- Done: read-only starter shortcuts.
- Missing: enable/suppress/release toggles, anti-repeat, action search, recorder, save/test/remove, templates and registered-hotkey list.

## Implementation order

1. Routine action editor with delay, condition and destination actions.
2. Settings and Hotkeys parity.
3. Responsive QA across every page and Quick Panel.
