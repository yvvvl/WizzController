# Legacy Flet retirement audit

This change removes the inactive Flet shell, its UI-only tests, its separate
build scripts, and its development dependency. The public product and release
builders already used Qt/PySide6 before this cleanup. `python main.py` remains
a compatibility shortcut to `qt_ui.run`.

## What stayed and why

- `config/paths.py` still recognizes `FLET_APP_STORAGE_DATA`, embedded Flet
  launchers, and old storage locations. This is user-data migration, not a
  runtime dependency on Flet. `tests/test_app_paths.py` covers Windows,
  Linux, macOS, and no-overwrite migration behavior.
- `config/app_runtime_manager.py` still recognizes a legacy packaged process
  when resolving an executable. Existing start-at-login settings may refer
  to an older installation; preserving this fallback avoids a silent change
  for upgrading users.
- Historical changelog entries and architecture decisions remain as records
  of earlier releases. They do not describe the current build target.

## Coverage transfer

| Former Flet-only tests | Current verification |
| --- | --- |
| Tray activation, Quick Panel, and window restoration | `test_qt_runtime.py`, `test_qt_run.py`, `test_single_instance.py` |
| Color, favorites, routines, targeting, and settings widgets | `test_qt_bridge.py`, `test_qt_hotkey_ui.py`, `test_wiz_color_pipeline.py`, and core service tests |
| Old installation storage | `test_app_paths.py` and `test_packaged_startup.py` |
| Legacy build metadata | `test_release_metadata.py` and the official Qt build workflows |

The former widget tests were intentionally **not** migrated line for line:
they asserted Flet control layout and event wiring that Qt does not use.
Equivalent user journeys need a manual desktop check on Windows and Linux;
unit tests alone cannot prove tray/compositor behavior, GPU rendering, or
physical bulb control. Use `docs/release-validation.md` before a release.

The supported Linux builder is `scripts/build_qt_linux.sh`, including on
native ARM64. The Windows builder is `scripts/build_qt_windows.ps1`.
The translation audit checks catalogs and Python UI calls; it does not parse
QML literals, so a zero hardcoded-string count is not a full QML language audit.
