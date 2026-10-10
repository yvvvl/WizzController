# Changelog

## v1.5.0

### Added

- Schedule existing routines locally by time and weekday on Windows and Linux.
  Choose a fixed bulb, group, or all lights as the default target; explicit
  targets on routine steps take priority. Edit, pause, resume, or delete each
  schedule and see its last result. Scheduling stays on your computer and uses
  the existing WiZ LAN controls—no cloud account or external scheduler.
- Set exact custom white temperatures (2200–6500 K) as Windows global hotkey
  actions. Custom color and white hotkeys now use the same visual picker as
  Color Studio; choosing a value does not change the light until the action
  is tested or triggered.

### Improved

- Capture shortcuts as a single key chord instead of editable free text.
  Distinguish the number row from Numpad digits and operators on Windows.
  Numpad shortcuts require native Windows registration; the keyboard fallback
  will not silently treat them as number-row shortcuts.
- Rebuild searchable action lists with aligned group labels, a clear selected
  state, keyboard navigation, more legible text, and smoother mouse-wheel
  scrolling. Filtering no longer leaves blank rows or stale scroll positions.
- Let the WizZ sidebar and title-bar marks follow the color of one online,
  lit bulb. With several bulbs, or when that bulb is off, they use the theme
  accent. The animation respects reduced-motion settings.
- Fix Spanish characters in the detached Windows updater progress window.

### Notes

- The app must remain running for local schedules to execute; it may stay in
  the tray. Missed times while the computer is off or asleep are not replayed.
  See the [schedule guide](docs/local-routine-schedules.md) for targeting,
  daylight-saving behavior, and supported routine steps.
- Global hotkeys remain Windows-only. macOS is still experimental and has no
  supported download in this release.

## v1.4.3

### Improved

- Control closing and minimizing independently: the X and minimize button can
  each hide the main window in the system tray, or use their normal behavior.
  Tray-only actions are disabled when the desktop has no system tray.
- Choose whether WizZ Desktop opens as a window or starts in the tray. If the
  tray is unavailable, it stays reachable, minimized in the taskbar. Existing
  "open minimized" settings migrate to the single tray-start option.
- Make Linux hotkey support explicit in the app: global shortcuts are not
  operational there yet, but saved shortcuts remain intact for future support.
- Keep virtual-light testing isolated while honoring the selected startup
  behavior; automated UI screenshots still open the window for inspection.

## v1.4.2

### Improved

- Create, edit, show or hide, and remove custom Quick Actions for power,
  brightness, white temperature, RGB color, and WiZ scenes. Up to six selected
  actions appear on Home and in the Quick Panel for the selected lights.
- Keep update progress visible while WizZ Desktop closes, replaces its files,
  and restarts on Windows. The separate progress window closes automatically
  after success and never blocks the update if it cannot be displayed.
- Keep checking for the detached updater's final result after restart, so a
  slower extraction or startup check cannot silently skip the completion
  notice inside WizZ Desktop.
- Make interface text easier to read with stronger Inter weights, larger labels
  and captions, and clearer secondary text in the Midnight theme. Navigation,
  light cards, Quick Actions, Settings, and the Quick Panel use the revised
  typography without clipping at the minimum window size.
- Strengthen page titles, connection status, and ON/OFF labels consistently,
  and align the Windows hotkey-status badge to the right edge of its header.
- Bundle a dedicated static ExtraBold Inter face for headings, light names,
  and power states so their visual weight is reliable across platforms.
- Restore the Windows sign-in startup switch in Qt Settings. It registers the
  packaged executable and prevents a development checkout from replacing the
  user's startup entry with the legacy launcher.
- Add the matching Linux start-at-login switch. The packaged build writes a
  per-user XDG autostart entry for its real executable, handles paths with
  spaces, and removes the entry when disabled or uninstalled.
- Size the offline-light cleanup button to its translated label so the Spanish
  text no longer clips inside the rounded control.
- Keep the retired Flet interface out of normal runtime dependencies while
  retaining its optional development and migration support.

## v1.4.1

### Improved

- Added a live progress indicator for update checks and downloads, including
  checksum verification and restart preparation.
- The updater now verifies that the updated app stays open during startup,
  restores the previous version if it fails, relaunches the restored app, and
  reports the outcome after restart.
- Fixed remaining Spanish labels in the English Color Studio and clarified the
  6500 K preset as “Cool White”.
- Made shortcut-setting descriptions and color presets wrap cleanly on narrow
  layouts instead of clipping or overflowing.
- Corrected the variable font family name so Windows uses its intended modern
  typeface rather than silently falling back to a generic font.
- Smoothed page transitions and standardized motion timing while preserving
  the reduced-motion setting.

## v1.4.0

### Highlights

- Rebuilt the desktop experience around a native Qt interface for Windows and
  Linux (x64 and ARM64), with English and Spanish UI.
- Redesigned Home, Color Studio, Favorites, Scenes, Routines, Hotkeys, Settings,
  and the multi-light controls for a more consistent, polished workflow.
- Added a movable Quick Panel that snaps to nearby screen edges, remembers its
  position, opens from the system tray, and dismisses when it loses focus. On
  Wayland, XWayland is selected when its runtime libraries are available.
- Expanded routines with ordered actions and targets for the current selection,
  all lights, or individual lights and groups.
- Added individual brightness controls, editable quick actions, and complete
  RGB/CCT editors with previews and quick values.
- Improved tray behavior, single-instance activation, close-to-tray handling,
  hotkeys, scrolling, and updater feedback.
- Added checksum-verified updates for installed Linux builds, with staged
  replacement and rollback if the updated app fails to start.
- Published portable Windows and Linux x64/ARM64 packages with SHA-256 checksums.

### Not included

- Screen Sync/Ambilight, audio sync, and RGBIC strip effects remain experimental
  and are not part of this public release.

### Support

WizZ Desktop is an independent project I build as a student. If it is useful to
you, you can support continued development through [GitHub Sponsors](https://github.com/sponsors/yvvvl). Thank you!

## v1.3.5

### Previous release

- Polished Qt transitions, updater feedback, hotkey status, and routine state
  capture; added individual light brightness controls.
- Added checksum-verified updates for installed Linux x64/ARM64 builds with
  staged replacement and rollback.

## v1.3.4

### Fixed

- Prevented the updater from locking the installed application directory while
  replacing it, and restored the previous build if the new executable failed
  to launch.
- Showed “Preparing…” while an update downloaded and verified instead of
  leaving the update-check button labeled “Checking…”.

## v1.3.3

### Fixed

- Embedded the WizZ light-bulb icon in the Windows executable so desktop
  shortcuts and Explorer no longer show a Python or generic icon.

## v1.3.0

### Added

- Persistent **Stable** and **Beta** update channels in Settings.
- Automatic updates for the portable Windows distribution: downloads the
  published ZIP, verifies its SHA-256 checksum, and replaces the app on restart.
- GitHub Releases publishing from `release/**` branches, with ZIP packages and
  checksums attached.

### Notes

- The first installation of v1.3.0 is still manual. Starting with that build,
  subsequent updates on the selected channel can be applied from the app.
- Builds run from source are not replaced automatically; they show the official
  download for installing the first portable build.
- Closed betas are not published in public GitHub Releases. Distribution
  requires a private repository or an update server with individual access;
  embedding a code in the app does not protect a public download.

## v1.2.0

### Added

- Temporary selection of one, several, or all bulbs without creating or editing
  persistent groups.
- Safe, manual checks for updates from GitHub Releases.
- A development fixture with virtual bulbs for validating targeting without
  requiring multiple physical devices.
- A Linux beta for Ubuntu Desktop: native package, XDG persistence,
  AppIndicator, access to Data/Logs, and per-user autostart.
- A Linux installer that needs no `sudo`, adds an application-menu launcher,
  and preserves personal data when uninstalled.

### Changed

- Windows builds store settings and logs in `%LOCALAPPDATA%\\WizZDesktop` and
  migrate data from previous Flet installations.
- A single click on the tray icon restores the main window.
- The experimental Quick Panel was removed from the public tray workflow.
- On Linux, global hotkeys are shown as unavailable: the app does not use
  `sudo` or attempt unsafe input-device hooks.

### Fixed

- Window restoration, actual exit from the tray, and single-instance behavior
  in Windows builds.
- Data persistence when replacing or running an isolated copy of the executable.
- The Linux package now includes the PyGObject/AppIndicator dependencies needed
  for the tray icon outside the development environment.

### Validation

- 368 automated tests completed on Windows and Ubuntu Desktop; i18n audit:
  608 English and Spanish keys, with no hardcoded UI strings.
- Real Windows validation: tray, hotkeys, single instance, AppData, clean
  extraction, and LAN control of a WiZ bulb.
- Real Linux beta validation: native build, extracted archive, tray, XDG
  persistence, and LAN control of the same WiZ bulb.

> RGBIC, Screen Sync, streaming, and automatic updates are not part of this
> stable release.

## v1.1.0

### Added

- Complete English and Spanish localization.
- Automatic system language detection.
- A manual language selector.
- A redesigned Favorites editor based on device capabilities:
  - RGB Color Studio editor.
  - White temperature and brightness editor.
  - WiZ scene selector.
  - Brightness-only editor.
- Improved Windows portable distribution.
- Third-party attribution and licensing documentation.

### Fixed

- Favorites editor retaining previous controls after changing type.
- RGB controls appearing in White, Scene, and Brightness favorites.
- UI refresh issues after changing favorite modes.
- Windows runtime packaging reliability.

### Technical

- 190 automated tests passing.
- Windows build verified.
- pywizlight license included in the distribution.

## 1.0.0 — release candidate

First desktop version prepared for Windows distribution.

### Included

- Local control of WiZ bulbs via native UDP.
- HSV, RGB/HEX, Kelvin whites, harmonies, moods, and recents in Color Studio.
- Scenes, favorites, and routines composed with `ActionSequenceExecutor`.
- Global hotkeys with a native Windows backend and selective fallback.
- System tray with quick actions and window recovery.
- Single-instance behavior with safe recovery from zombie desktop sessions.
- Responsive UI for Home, Color, Scenes, Favorites, Routines, Settings, and
  Hotkeys.
- Persistent settings and logs outside the installation directory in Flet
  builds.
- Reproducible `flet build windows` pipeline and GitHub Actions artifact.

### Removed before v1

- Voice recognition and voice commands.
- The `faster-whisper`, `sounddevice`, and `numpy` dependencies associated with
  voice features.

### Validation pending before publishing the final tag

- Smoke test of the executable on real Windows.
- Startup with Windows from the packaged launcher.
- Tray, hotkeys, and single-instance behavior after suspend/resume.
- Final verification of the ZIP and checksum generated by the Windows workflow.
