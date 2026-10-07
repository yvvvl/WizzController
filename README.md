<div align="center">

[Español](README.es.md) · **English**

<img src="assets/icon_windows.png" alt="WizZ Desktop" width="112" />

# WizZ Desktop

### Fast, private, local control for WiZ smart lights

[![Release](https://img.shields.io/github/v/release/yvvvl/WizzController?label=release)](https://github.com/yvvvl/WizzController/releases/latest)
[![CI](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml)
[![Windows Build](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml)
[![Python](https://img.shields.io/badge/Python-3.11%20%E2%80%93%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/UI-Qt%20%2F%20PySide6-41CD52)](https://www.qt.io/)

[Download the latest release](https://github.com/yvvvl/WizzController/releases/latest) · [Report an issue](https://github.com/yvvvl/WizzController/issues)

</div>

---

## About WizZ Desktop

**WizZ Desktop** is a desktop application for controlling WiZ lights directly
over your local network. Normal commands use the native WiZ UDP LAN protocol,
so light control does not depend on the WiZ cloud and remains responsive when
Internet access is unavailable.

Windows and Linux (x64 and ARM64) are supported desktop platforms. Linux
packages target Ubuntu-compatible desktops and install per user without `sudo`.
There is no supported macOS download in this release yet.

> Latest stable release: **[v1.4.3](https://github.com/yvvvl/WizzController/releases/tag/v1.4.3) · build 3**

### New in v1.4.3

- Decide independently whether the **X** and **minimize** button hide the app
  in the system tray. Normal closing and taskbar minimization remain available.
- Choose **Open window** or **Start in tray** at launch. If the desktop has no
  tray, the app stays reachable, minimized in the taskbar.
- The Linux Hotkeys page now clearly explains that global shortcuts are not
  operational there yet; saved shortcuts are preserved.

See the [full v1.4.3 changelog](CHANGELOG.md#v143).

## v1.4.3 release validation guide

This guide applies to the published native **Qt desktop** build. The Windows
installer is the simplest option. If you prefer the portable ZIP, extract it
first and keep `_internal` next to `WizZDesktop.exe`.

### Install and launch commands (Windows PowerShell)

Download `WizZDesktop-v1.4.3-windows-x64.zip` and its `.sha256` file from the
release, then run the following. Change `$download` only if the files
were saved somewhere other than Downloads.

```powershell
$download = "$env:USERPROFILE\Downloads"
$zip = Join-Path $download "WizZDesktop-v1.4.3-windows-x64.zip"
$checksum = "$zip.sha256"
$target = Join-Path $download "WizZDesktop-v1.4.3"

Get-FileHash -LiteralPath $zip -Algorithm SHA256
Get-Content -LiteralPath $checksum
Expand-Archive -LiteralPath $zip -DestinationPath $target -Force
Set-Location $target
.\WizZDesktop.exe
```

The hash printed by `Get-FileHash` must match the hash in the `.sha256` file.
Before testing, close every other WizZ Desktop copy and back up
`%LOCALAPPDATA%\WizZDesktop` if it contains settings you want to keep.

### What to test

Use real WiZ lights on the same LAN where possible. For every test, note
**PASS**, **FAIL**, or **N/A**, plus the expected and actual result.

1. **Connection and targeting:** in Settings, scan for lights; also try adding
   one known IP manually. Select one light, several lights, and all lights.
2. **Home controls:** toggle power; set brightness to 20%, 50%, and 100%; then
   apply red, green, blue, warm white, and cool white. Confirm the physical
   light matches the UI for one and multiple selected lights.
3. **New UI:** resize the window, switch themes, inspect long dropdowns, cards,
   centered option labels, rounded lists, and theme tint. Restart the app and
   confirm the chosen theme and saved items persist.
4. **Favorites and Color:** create RGB and CCT-white favorites. Test the quick
   swatches, HEX/Kelvin field, picker cursor, preview, saving, reopening, and
   applying each favorite.
5. **Scenes and routines:** create a local scene using a name (not an ID). Make
   a routine with power, RGB color, CCT white, wait, and scene steps; reorder
   steps, save, reopen, and execute it. Apply several named WiZ scenes.
6. **Quick Panel:** open it from the tray menu (or a shortcut on Windows), use
   the bulb carousel, select bulbs on later pages, and verify that selection
   does not reset the current page. Test arrows/page buttons, placement beside
   the taskbar on each monitor, dragging and snapping to each screen edge,
   remembered placement after reopening, click-outside dismissal, and edited
   quick actions.
7. **Hotkeys and tray:** on Windows, assign a non-conflicting shortcut, restart,
   and check one action occurs per press. On Linux, confirm the Hotkeys page
   explains that global shortcuts are not yet operational. On both systems,
   test restoring from the tray and the separate close/minimize settings.

### Integrations and known boundaries

- **WiZ LAN:** discovery, manual IP setup, power, brightness, RGB, CCT white,
  named scenes, multi-selection, favorites, routines, and tray are the
  integrations to exercise. Global hotkeys currently work on Windows only.
- **WiZ mobile-app state changes:** if you change a light in the mobile app,
  record whether the desktop view follows it and how long it takes. This is
  observational testing, not a guarantee for every model/firmware.
- **Not included:** screen sync/Ambilight, audio sync, experimental strip effects,
  and an FPS loop. Do not report these as failures;
  mark them **N/A**.

### Run the v1.4.3 source (contributors only)

Do not use these commands to validate a downloaded release: a source run is
not the packaged executable. In PowerShell:

```powershell
git clone --branch v1.4.3 --depth 1 https://github.com/yvvvl/WizzController.git
Set-Location .\WizzController
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m qt_ui.run
.\.venv\Scripts\python.exe -m pytest -q
```

For UI testing without physical lights, set `WIZZ_DEV_VIRTUAL_BULBS=3` only
for that launch. Do not set it when testing your real light.

### Send a useful report

Include app version (`1.4.3`), operating system and display scale, light model
and firmware, the exact steps, expected versus actual behavior, repeatability,
and a short screenshot/video when useful. To inspect the local log without
sharing private configuration files:

```powershell
Get-Content "$env:LOCALAPPDATA\WizZDesktop\logs\wizz.log" -Tail 200
```

Redact IP addresses, MAC addresses, access tokens, and private files before
sharing a report.

## Included in v1.4.3

- Native Qt desktop app for Windows and Linux (x64 and ARM64), with English and
  Spanish UI.
- Control one, several, or all lights with power, per-light brightness, RGB,
  tunable white, WiZ scenes, favorites, and routines.
- Movable Quick Panel with edge snapping, remembered placement, tray access,
  editable quick actions, and click-outside dismissal.
- Tray controls, single-instance activation, independent close/minimize-to-tray
  options, and a simple window-or-tray startup choice. Global hotkeys are
  available on Windows; the Linux Hotkeys page states the current limitation.
- Checksum-verified updates for portable Windows and installed Linux builds.
- Persistent settings, favorites, device names, and logs; native Linux XDG
  storage, AppIndicator tray support, and per-user installation.

> Screen Sync and audio sync are not included in this public release.

WizZ Desktop is an independent project I build as a student. If it is useful to
you, you can support development through [GitHub Sponsors](https://github.com/sponsors/yvvvl); no pressure—feedback and issue reports help too.

---

## Main features

### Local WiZ control

- Power, brightness, RGB color, and Kelvin white temperature.
- Official WiZ scenes.
- Synchronization with changes made from the WiZ mobile app.
- Hybrid discovery through local UDP and `pywizlight` support.
- Manual light setup by IP address.
- Temporary targeting of one, multiple, or all available lights.

### Color Studio

- Perceptual hue and saturation picker.
- Separate brightness and white-temperature controls.
- Precise HEX, RGB, hue, and saturation editing.
- Live or manual application.
- Recent colors, favorites, and presets.
- Conversion from logical color to physical WiZ RGBTW channels.

### Automation

- Favorites for frequently used settings.
- Multi-step routines.
- Color, white, brightness, scene, and delay actions.
- Centralized execution through `ActionSequenceExecutor`.

### Desktop integration

**Windows**

- Native global hotkeys through `RegisterHotKey`.
- System tray, independent close/minimize-to-tray options, window-or-tray
  startup, and Windows start-at-login.
- Single-instance activation and restoration.

**Linux desktop**

- AppIndicator tray integration on supported desktops.
- XDG-compliant persistent storage.
- Per-user autostart and desktop application launcher.
- Global hotkeys are not operational on Linux yet; saved shortcuts are kept
  for future support. Running the application as root is neither required nor
  recommended.

---

## Installation

### Windows 10/11 x64

1. Open the [latest release](https://github.com/yvvvl/WizzController/releases/latest).
2. Download and run `WizZDesktop-v1.4.3-windows-x64-setup.exe`, or download
   `WizZDesktop-v1.4.3-windows-x64.zip` for a portable copy.
3. If using the ZIP, extract the complete archive and run `WizZDesktop.exe`.

Windows may display a SmartScreen warning because the installer and app are
not yet digitally signed. Confirm that you downloaded them from this
repository; if using the portable ZIP, also verify its published checksum
before deciding whether to run it.

### Linux (x64 and ARM64)

Native x64 and ARM64 bundles are provided for Ubuntu-compatible desktop systems.

1. Download the archive that matches your CPU from the latest release: `linux-x64` for Intel/AMD, or `linux-arm64` for 64-bit ARM.
2. Extract the archive.
3. Open a terminal in the extracted directory and run:

```bash
./install.sh
```

4. Open **WizZ Desktop** from your applications menu. You may pin it to your
   dock like any other desktop application. Once installed, use **Settings →
   Check for updates → Install and restart** for future updates.

On Wayland, WizZ Desktop prefers XWayland when its XCB runtime libraries are
available so the Quick Panel can be positioned and snapped to screen edges.
If startup reports missing XCB libraries, install `libxcb-cursor0`,
`libxcb-icccm4`, and `libxcb-keysyms1`. An explicitly selected Wayland backend
leaves window placement to the desktop compositor.

To uninstall the per-user installation:

```bash
./uninstall.sh
```

### Verify downloads

Windows PowerShell:

```powershell
Get-FileHash .\WizZDesktop-v1.4.3-windows-x64.zip -Algorithm SHA256
```

Linux:

```bash
sha256sum -c WizZDesktop-v1.4.3-linux-<architecture>.tar.gz.sha256
```

Compare the result with the checksum published alongside the release assets.

Maintainers can emulate Ubuntu ARM64 from a Windows x64 computer for package
and startup checks. See [the ARM64 emulation guide](docs/arm64-emulation.md).

---

## Basic use

1. Make sure your computer and WiZ lights are on the same local network.
2. Open WizZ Desktop and wait for discovery to complete.
3. Select one, several, or all lights from the target selector.
4. Use Home, Color, Scenes, Favorites, or Routines to control the selection.
5. Open **Settings → About** to locate your persistent data and logs or to check
   for a new release.

If discovery is blocked by a firewall or network isolation, add the light
manually using its local IP address.

---

## Development

### Requirements

- Python 3.11 to 3.13.
- A local network for real light tests, or the built-in virtual-light developer
  environment.

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m qt_ui.run
```

### Linux

Use a supported Python 3.12 interpreter (some newer distributions default to
Python 3.14, which is not supported by this project yet).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-qt-linux.txt -r requirements-dev.txt
python -m qt_ui.run
```

### Validation

```bash
python -m pytest -q
python -m compileall -q main.py app_meta.py core config qt_ui localization tests tools
python tools/i18n_audit.py
git diff --check
```

### Virtual lights

Developer mode can launch virtual WiZ lights to exercise targeting, power,
brightness, RGB, white temperature, and scenes without owning multiple physical
bulbs. The Qt source run also accepts `WIZZ_DEV_VIRTUAL_BULBS=3`: launch with
`$env:WIZZ_DEV_VIRTUAL_BULBS = "3"; python -m qt_ui.run` in PowerShell or
`WIZZ_DEV_VIRTUAL_BULBS=3 python -m qt_ui.run` on Linux. This uses an isolated
test profile, sends no WiZ LAN traffic, and is unavailable in packaged builds.
Create a routine with a targeted “Turn off” step to verify that only one virtual
bulb changes. For two or more lights, click “Multiple…” beside the step target;
save the selection as a named group to reuse it
across routines. See the developer documentation under `docs/` for more detail.

### Native builds

Windows:

```powershell
.\scripts\build_qt_windows.ps1 -Clean
```

Linux:

```bash
python -m pip install -r requirements-build.txt
PYTHON="$(command -v python)" bash scripts/build_qt_linux.sh --clean
```

---

## Data and privacy

WizZ Desktop does not require its own account or remote database for LAN light
control. Personal JSON files are excluded from version control because they may
contain IP addresses, MAC addresses, hotkeys, and local preferences.

Development checkout:

```text
config/json/
```

Packaged Windows application:

```text
%LOCALAPPDATA%\WizZDesktop\config
%LOCALAPPDATA%\WizZDesktop\logs
```

Installed Linux application:

```text
~/.config/WizZDesktop/config
~/.local/state/WizZDesktop/logs
~/.local/share/WizZDesktop
```

Storage from earlier Flet builds is migrated automatically when necessary. The
actual locations can also be opened from **Settings → About → Data/Logs**.

---

## Architecture

The project separates platform-independent lighting behavior from desktop
integration:

```text
UI (Qt / PySide6)
  → application services and action sequences
    → WiZ LAN controller and persistence

platform boundary
  → Windows services
  → Linux services
  → safe unsupported fallbacks
```

This keeps targeting, color conversion, routines, and persistence testable
without depending on a particular desktop environment.

## Repository structure

```text
app_meta.py   Product metadata, version, and identifiers
core/         WiZ control, actions, hotkeys, tray, single instance, and logging
config/       Persistent configuration and JSON managers
ui/           Flet application and components
assets/       Icons and visual resources
docs/         Guides, decisions, plans, and checklists
scripts/      Validation, installers, and Windows/Linux builds
tools/        Diagnostics and developer probes
tests/        Core, UI, runtime, and packaging tests
```

---

## Project status

This source is v1.4.3; download a packaged build from GitHub Releases to test
the actual distribution. The experimental local Govee work is on a separate
feature branch and is not part of the current Qt user interface.

In v1.4.3, **Settings → Quick Actions** lets you create, edit,
show/hide, and delete custom controls for power, brightness, Kelvin white, RGB,
and WiZ scenes. Up to six selected actions appear in both Home and the Quick
Panel. These controls operate on the currently selected lights.

The Qt/PySide6 shell is the only supported desktop interface. The retired Flet
source remains isolated for data-migration and historical test coverage; it is
not launched or packaged for users. Flet is an optional `legacy-flet` dependency,
not a default runtime dependency; the development requirements still include it
to run the historical tests.

## Author

Developed by **Ignacio** (`yvvvl`) as a personal desktop application for local
WiZ lighting control.

## Acknowledgements

- [pywizlight](https://github.com/sbidy/pywizlight)
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/)
- [pystray](https://github.com/moses-palmer/pystray)
- Community testers who reported practical Windows and Linux issues.

---

If WizZ Desktop is useful to you, consider starring the repository or sharing
clear reproduction steps through the issue tracker.
