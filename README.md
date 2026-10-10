<div align="center">

[Español](README.es.md) · **English**

<img src="assets/icon_windows.png" alt="WizZ Desktop" width="112" />

# WizZ Desktop

### Local control for WiZ smart lights

[![Release](https://img.shields.io/github/v/release/yvvvl/WizzController?label=release)](https://github.com/yvvvl/WizzController/releases/latest)
[![CI](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml)
[![Windows and Linux build](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml)

[Download](https://github.com/yvvvl/WizzController/releases/latest) · [Report an issue](https://github.com/yvvvl/WizzController/issues) · [Support development](https://github.com/sponsors/yvvvl)

</div>

---

WizZ Desktop controls WiZ bulbs on your local network. Everyday light
commands use the WiZ UDP LAN protocol rather than a cloud service. The
supported desktop app uses Qt/PySide6 and is available for **Windows x64**
and **Ubuntu-compatible Linux x64/ARM64**. macOS remains experimental.

## What's in v1.5.0

- Schedule existing routines locally by time and weekday, with a fixed bulb
  or saved group as the default target. Edit or pause schedules in the app.
- Record Windows shortcuts as real key chords, distinguish Numpad keys from
  the number row, and choose exact-Kelvin white actions visually.
- Browse clearer action lists, use the refined Color Studio picker, and see
  the WizZ mark react to one active bulb's color.

Read the [full changelog](CHANGELOG.md#v150). The app must stay running for
schedules, even if hidden in the tray; missed times are not replayed. Global
hotkeys are currently Windows-only. Screen Sync and audio sync are not part
of this release.

## Get started

1. [Download the latest release](https://github.com/yvvvl/WizzController/releases/latest).
   Windows offers a setup executable or a portable ZIP; Linux offers x64 and
   ARM64 archives with a per-user installer. ZIP/tar downloads have SHA-256
   sidecars.
2. Install or extract the full package, then open **WizZ Desktop**. Keep the
   `_internal` directory beside the Windows portable executable.
3. Connect your computer and WiZ bulbs to the same local network. Find bulbs
   in **Settings**, or add a known local IP manually.
4. Select one, several, or all bulbs and use Home, Color Studio, Scenes,
   Favorites, Routines, or the Quick Panel.

Supported installations can update from **Settings → Check for updates →
Install and restart**. See the [installation guide](docs/installation.md)
for checksums, Linux desktop requirements, data locations, and uninstalling.

## What it does

| Area | Highlights |
| --- | --- |
| Lights | Power, brightness, RGB, Kelvin whites, WiZ scenes, discovery, manual IP, and multi-bulb targeting. |
| Color Studio | Hue/saturation palette, independent brightness and CCT, exact values, recent colors, and favorites. |
| Automation | Multi-step routines, saved groups, and local weekday/time schedules. |
| Desktop | Movable edge-snapping Quick Panel, system tray, start-at-login, themes, English/Spanish UI, and in-app updates. |
| Windows hotkeys | Native global shortcuts with Numpad distinction and custom RGB/Kelvin actions. |

Normal lighting control stays on the LAN. Settings and logs are stored on
your computer; they may include bulb IP/MAC addresses and should be redacted
before sharing. See [installation and data paths](docs/installation.md#checksum-and-saved-data).

## Documentation and development

- [Documentation index](docs/README.md): English and Spanish guides.
- [Release validation](docs/release-validation.md): real-light, tray, and
  packaged-update checklist.
- [Local routine schedules](docs/local-routine-schedules.md): target and
  clock behavior, limitations, and tests.
- [Development](docs/development.md): source setup, virtual bulbs, tests,
  architecture, and release builders.

For a source run, install the requirements and start `python -m qt_ui.run`.
Set `WIZZ_DEV_VIRTUAL_BULBS=3` only when you want a separate simulated test
profile with no WiZ LAN traffic. Packaged public builds ignore that flag.

The supported interface and builders live in `qt_ui/` and the `build_qt_*`
scripts. `ui/` contains retired Flet code retained for migration and
historical tests; it is not packaged or launched for users. See the
[current/legacy path map](docs/development.md#current-and-legacy-paths)
before changing or removing those files.

## Project and acknowledgements

WizZ Desktop is an independent project by **Ignacio** (`yvvvl`), not
affiliated with WiZ Connected or Signify. If it is useful, you can
[support its development](https://github.com/sponsors/yvvvl); feedback and
reproducible issue reports also help.

The repository does **not yet have a project-wide license selected**.
[Third-party notices](THIRD_PARTY_NOTICES.md) and the files in `licenses/`
cover dependencies and bundled assets, not the project's own source.
