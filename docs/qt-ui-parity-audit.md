# Qt desktop capability audit (v1.5.0)

This is a **current capability map**, not the original Flet-to-Qt migration
checklist. The former checklist said that tray lifecycle, localization,
routine editing, settings, and hotkeys were missing; those statements became
obsolete as the Qt interface was completed. The supported desktop UI is
`qt_ui/`. See [development](development.md#current-source-paths) for the
current code boundary and data-migration compatibility.

| Area | Present in the Qt desktop | Where to inspect |
| --- | --- | --- |
| Shell and Quick Panel | Native Qt window, themed navigation, tray integration, movable/snap-capable Quick Panel, persisted position and visibility behavior | [`Main.qml`](../qt_ui/qml/Main.qml), [`QuickPanel.qml`](../qt_ui/qml/QuickPanel.qml), [`runtime.py`](../qt_ui/runtime.py) |
| Home and targeting | Single/multiple/all bulb selection, power, brightness, quick actions, device status | [`Main.qml`](../qt_ui/qml/Main.qml), [`LightCard.qml`](../qt_ui/qml/LightCard.qml), [`bridge.py`](../qt_ui/bridge.py) |
| Color Studio | RGB palette, Kelvin whites, independent brightness, HEX and recent/favorite controls | [`ColorPage.qml`](../qt_ui/qml/ColorPage.qml), [`WizColorPicker.qml`](../qt_ui/qml/WizColorPicker.qml) |
| Scenes and favorites | WiZ scenes plus local scene/favorite creation and application | [`ScenesPage.qml`](../qt_ui/qml/ScenesPage.qml), [`FavoritesPage.qml`](../qt_ui/qml/FavoritesPage.qml) |
| Routines | Multi-step editor, targets/groups, execution, local time-and-weekday schedules | [`RoutinesPage.qml`](../qt_ui/qml/RoutinesPage.qml), [schedule guide](local-routine-schedules.md) |
| Settings | Language, theme, device setup, tray/startup behavior, quick-action editor, in-app updates with progress | [`SettingsPage.qml`](../qt_ui/qml/SettingsPage.qml), [`QuickActionsEditor.qml`](../qt_ui/qml/QuickActionsEditor.qml) |
| Hotkeys | Windows shortcut capture/registration, Numpad distinction, custom RGB and Kelvin picker | [`HotkeysPage.qml`](../qt_ui/qml/HotkeysPage.qml), [`global_hotkeys.py`](../core/global_hotkeys.py) |

Automated coverage includes Qt bridge/runtime, UI models, schedules, hotkeys,
and packaging tests under `tests/`. The
[manual release checklist](release-validation.md) is still required to verify
physical WiZ devices, tray behavior, multi-monitor placement, and packaged
updates. This table is not a claim of pixel-for-pixel Flet parity or complete
hardware compatibility.

## Current limits

- Global hotkeys are operational on Windows, not Linux. Saved Linux shortcuts
  remain in configuration until a safe backend is available.
- Linux tray support depends on AppIndicator; a forced Wayland backend can
  limit exact Quick Panel placement.
- macOS is an experimental smoke-build target, not a supported release.
- Screen Sync/Ambilight and audio sync are not included in the Qt release.
- Local routine schedules require the app to keep running and do not replay
  missed times after sleep or shutdown.

Update this map when a capability is shipped or removed; put prospective
design ideas in separate proposals, not in a permanently stale “missing” list.
