# v1.2.0 release preparation

Status: Ready for owner approval after final artifact checksums

Date: 2026-08-28

## Release channels

- **Windows x64:** stable public release.
- **Linux x64:** clearly labelled Ubuntu Desktop beta in the same GitHub
  release.
- **RGBIC:** excluded from v1.2.0; it remains a separate closed beta after the
  public release is approved.

## Included in v1.2.0

- Temporary selection of one, several or all saved WiZ lights, without
  maintaining persistent groups.
- Read-only update check that opens the official GitHub Release page; it never
  downloads, replaces or restarts the app automatically.
- More reliable tray restoration, real tray exit and single-instance handling.
- Persistent packaged settings and logs: `%LOCALAPPDATA%\\WizZDesktop` on
  Windows; XDG configuration and state directories on Linux.
- Native Linux beta package for Ubuntu Desktop with AppIndicator tray,
  XDG autostart, `xdg-open` integration and an intentional no-hotkeys state.

## Explicit exclusions

- RGBIC production support, streaming, Screen Sync and an effects scheduler.
- Automatic updater installation or rollback.
- Quick Panel; the experimental window was removed from the public v1.2 flow.
- macOS support.

## Evidence recorded

- Automated validation: `368 passed, 98 warnings` on Windows and Ubuntu
  Desktop.
- Localization audit: `608` keys in `en`/`es`, no hardcoded UI strings.
- Windows: real WiZ LAN validation for power, brightness, RGB, Kelvin and a
  built-in scene; packaging, AppData migration, tray and single-instance smoke.
- Linux: native package built and launched outside the repository on Ubuntu
  22.04 GNOME/Wayland; AppIndicator tray, XDG persistence and WiZ LAN control
  were manually verified.
- GTK/Flutter shutdown warnings observed only after normal exit are upstream
  runtime cleanup warnings, not WizZ failures.

## Assets to attach

1. `WizZDesktop-v1.2.0-windows-x64.zip`
2. `WizZDesktop-v1.2.0-windows-x64.zip.sha256`
3. `WizZDesktop-v1.2.0-linux-x64.tar.gz`
4. `WizZDesktop-v1.2.0-linux-x64.tar.gz.sha256`

## Publication gate

The public tag and GitHub Release remain intentionally uncreated. Before
publication, merge the approved Linux changes into the chosen release branch,
rebuild both platform artifacts from that same final commit, record both
checksums, review the release diff, and obtain owner approval.
