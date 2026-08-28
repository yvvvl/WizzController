<div align="center">

[Español](README.es.md) · **English**

<img src="assets/icon_windows.png" alt="WizZ Desktop" width="112" />

# WizZ Desktop

### Fast, private, local control for WiZ smart lights

[![Release](https://img.shields.io/github/v/release/yvvvl/WizzController?label=release)](https://github.com/yvvvl/WizzController/releases/latest)
[![CI](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml)
[![Windows Build](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml)
[![Python](https://img.shields.io/badge/Python-3.11%20%E2%80%93%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.85.2-6C63FF)](https://flet.dev/)

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

## What is new in v1.2.0

- Quickly select one, several, or all discovered lights.
- Manually and safely check GitHub Releases for updates.
- Preserve settings, favorites, lights, and logs between application updates.
- Predictably restore the main window from the system tray.
- Enforce a single running instance of the application.
- Provide a native Linux beta with XDG storage, AppIndicator tray support,
  per-user autostart, and an installer that does not require `sudo`.

> RGBIC, Screen Sync, streaming, and automatic installation of updates are not
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

### Linux x64 beta

The beta was validated on Ubuntu 22.04 with GNOME/Wayland.

1. Download `WizZDesktop-v1.2.0-linux-x64.tar.gz` from the latest release.
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
sha256sum -c WizZDesktop-v1.2.0-linux-x64.tar.gz.sha256
```

Compare the result with the checksum published alongside the release assets.

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
python main.py
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python main.py
```

### Validation

```bash
python -m pytest -q
python -m compileall -q main.py app_meta.py core config ui localization tests tools
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
flet build windows
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

Previous Flet storage is migrated automatically when necessary. The actual
locations can also be opened from **Settings → About → Data/Logs**.

---

## Architecture

The project separates platform-independent lighting behavior from desktop
integration:

```text
UI (Flet)
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

The Quick Panel redesign remains paused, and experimental RGBIC behavior stays
outside the public stable channel until it receives dedicated hardware testing.

## Author

Developed by **Ignacio** (`yvvvl`) as a personal desktop application for local
WiZ lighting control.

## Acknowledgements

- [pywizlight](https://github.com/sbidy/pywizlight)
- [Flet](https://flet.dev/)
- [pystray](https://github.com/moses-palmer/pystray)
- Community testers who reported practical Windows and Linux issues.

---

If WizZ Desktop is useful to you, consider starring the repository or sharing
clear reproduction steps through the issue tracker.
