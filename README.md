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

Windows is the stable platform. Linux is available as a beta for Ubuntu Desktop
and compatible environments.

> Current public release: **v1.2.0 · build 2**

## Closed beta v1.4.0b1 — tester guide

This section applies only to the private **Qt preview** release. It is separate
from the public stable release and requires an invited GitHub account. It is a
portable Windows build: do not run it from inside the ZIP and keep `_internal`
next to `WizZDesktop.exe`.

### Install and launch commands (Windows PowerShell)

Download `WizZDesktop-v1.4.0b1-windows-x64.zip` and its `.sha256` file from the
private release, then run the following. Change `$download` only if the files
were saved somewhere other than Downloads.

```powershell
$download = "$env:USERPROFILE\Downloads"
$zip = Join-Path $download "WizZDesktop-v1.4.0b1-windows-x64.zip"
$checksum = "$zip.sha256"
$target = Join-Path $download "WizZDesktop-v1.4.0b1"

Get-FileHash -LiteralPath $zip -Algorithm SHA256
Get-Content -LiteralPath $checksum
Expand-Archive -LiteralPath $zip -DestinationPath $target -Force
Set-Location $target
.\WizZDesktop.exe
```

The hash printed by `Get-FileHash` must match the hash in the `.sha256` file.
Before testing, close every other WizZ Desktop copy and back up
`%LOCALAPPDATA%\WizZDesktop` if it contains settings you want to keep. The beta
uses that same local data folder.

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
6. **Quick Panel:** open it through its configured shortcut, use the bulb
   carousel, select bulbs on later pages, and verify that selection does not
   reset the current page. Test arrows/page buttons, placement beside the
   taskbar on each monitor, click-outside dismissal, and edited quick actions.
7. **Hotkeys and tray:** assign a non-conflicting shortcut, restart, and check
   one action occurs per press with no long freeze. Test restoring from tray and
   closing/minimizing behavior.

### Integrations and known boundaries

- **WiZ LAN:** discovery, manual IP setup, power, brightness, RGB, CCT white,
  named scenes, multi-selection, favorites, routines, tray, and hotkeys are
  the integrations to exercise.
- **WiZ mobile-app state changes:** if you change a light in the mobile app,
  record whether the desktop view follows it and how long it takes. This is
  observational testing, not a guarantee for every model/firmware.
- **Not included:** screen sync/Ambilight, audio sync, experimental strip effects,
  an FPS loop, and private-beta auto-updates. Do not report these as failures;
  mark them **N/A**.

### Optional source-run commands (contributors only)

Do not use these when validating the downloaded build. They are for a tester
who was explicitly given access to the source repository:

```powershell
git clone https://github.com/yvvvl/WizzController-Beta.git
Set-Location .\WizzController-Beta
git switch beta/v1.4.0
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m qt_ui.run
python -m pytest -q
```

### Send a useful report

Include app version (`1.4.0b1`), Windows version and display scale, light model
and firmware, the exact steps, expected versus actual behavior, repeatability,
and a short screenshot/video when useful. To inspect the local log without
sharing private configuration files:

```powershell
Get-Content "$env:LOCALAPPDATA\WizZDesktop\logs\wizz.log" -Tail 200
```

Redact IP addresses, MAC addresses, access tokens, and private beta files
before sending anything outside the invited group. The full release checklist
is also attached to the private release as `BETA_TESTING_EN.md`.

## What is new in v1.2.0

- Quickly select one, several, or all discovered lights.
- Stable/Beta channels and checksum-verified automatic updates for portable
  Windows builds from version 1.3.0.
- Preserve settings, favorites, lights, and logs between application updates.
- Predictably restore the main window from the system tray.
- Enforce a single running instance of the application.
- Provide a native Linux beta with XDG storage, AppIndicator tray support,
  per-user autostart, and an installer that does not require `sudo`.

> Screen Sync, streaming, and automatic installation of updates are not
> included in this public release.

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
- System tray, close-to-tray, minimized startup, and Windows startup.
- Single-instance activation and restoration.

**Linux beta**

- AppIndicator tray integration on supported desktops.
- XDG-compliant persistent storage.
- Per-user autostart and desktop application launcher.
- Global hotkeys are deliberately disabled when no safe, compatible desktop
  shortcut portal is available. Running the application as root is neither
  required nor recommended.

---

## Installation

### Windows 10/11 x64

1. Open the [latest release](https://github.com/yvvvl/WizzController/releases/latest).
2. Download `WizZDesktop-v1.2.0-windows-x64.zip`.
3. Extract the complete ZIP archive.
4. Run `WizZDesktop.exe`.

Windows may display a SmartScreen warning because the executable is not yet
digitally signed. Select **More info → Run anyway** only if you downloaded the
file from this repository and verified its checksum.

### Linux beta (x64 and ARM64)

The beta was validated on Ubuntu 22.04 with GNOME/Wayland.

1. Download the archive that matches your CPU from the latest release: `linux-x64` for Intel/AMD, or `linux-arm64` for 64-bit ARM.
2. Extract the archive.
3. Open a terminal in the extracted directory and run:

```bash
./install.sh
```

4. Open **WizZ Desktop** from your applications menu. You may pin it to your
   dock like any other desktop application.

To uninstall the per-user installation:

```bash
./uninstall.sh
```

### Verify downloads

Windows PowerShell:

```powershell
Get-FileHash .\WizZDesktop-v1.2.0-windows-x64.zip -Algorithm SHA256
```

Linux:

```bash
sha256sum -c WizZDesktop-v1.2.0-linux-<architecture>.tar.gz.sha256
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

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
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
bulbs. See the developer documentation under `docs/` for the current workflow.

### Native builds

Windows:

```powershell
.\scripts\build_qt_windows.ps1 -Clean
```

Linux:

```bash
bash scripts/build_linux.sh --clean
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

Version `v1.2.0` is publicly available as a stable portable Windows x64 build
and a native Linux x64 beta. The next cycle, `v1.3.0`, focuses on an elegant,
minimal, responsive UI refactor while preserving the current control path and
resource efficiency.

The Qt/PySide6 shell is the only supported desktop interface. The retired Flet
source remains isolated for data-migration and historical test coverage; it is
not launched or packaged for users.

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
