# Cross-platform Foundation Phase 2

Date: 2026-08-25  
Status: In Progress

## Objective

Start the Linux beta boundary without changing the WiZ core, `LightController`,
the existing Windows runtime, or the RGBIC contracts.

## Implemented

- Added explicit Linux capability detection.
- Added an XDG user autostart service.
- Added an `xdg-open` system integration service.
- Added a callback-based Linux window boundary for future Flet/compositor wiring.
- Added an isolated `LinuxTrayBackend` with injectable icon factory and
  lifecycle tests; it is not wired into the product runtime yet.
- Added tests for Wayland permission degradation, autostart, folder opening and
  independent window capabilities.
- Added a CI smoke matrix for Ubuntu, macOS and Windows that compiles and tests
  the platform boundary without starting the desktop application.

## Deliberate limitations

- The new services are not wired into `main.py` yet.
- No Linux tray backend is enabled in the product runtime.
- Global hotkeys remain capability-reported as degraded on X11 and permission
  required on Wayland; no backend replacement was introduced.
- Single-instance activation is explicitly unavailable until a portable
  activation mechanism is designed.
- No Linux package or macOS backend is produced in this phase.

## Decisions preserved

- `LightController` and `WizProtocol` remain unchanged.
- There are no operating-system forks of the WiZ core.
- Capability states are explicit instead of silently pretending support.
- Tests do not access hardware or the network.

## Validation

Focused platform tests: 27 passed locally.

Full-suite validation on the Ubuntu 22.04 VM: 323 passed, 98 warnings.

### Real VM evidence (2026-08-27)

The VM reports:

- Python 3.11.0rc1;
- `XDG_SESSION_TYPE=wayland`;
- `DISPLAY=:0`;
- `WAYLAND_DISPLAY=wayland-0`;
- `/usr/bin/xdg-open` available.

Capability detection returned:

- hotkey registration and recording: `permission_required`;
- tray: `available`;
- tray default action: `degraded`;
- start at login: `available` through XDG autostart;
- window operations and work-area positioning: `degraded`;
- single-instance exclusion: `degraded`;
- single-instance activation: `unavailable`;
- folder opening: `available` through `xdg-open`.

The first probe using `vars()` failed because `DesktopCapabilities` uses
slotted dataclasses. The dataclass `fields()` probe succeeded and is now the
documented inspection method.

## Next steps

1. Test the tray adapter manually on the Ubuntu Wayland VM.
2. Decide the X11/Wayland hotkey strategy and permission messaging.
3. Add Linux/macOS CI smoke jobs.
4. Wire services only after manual Linux desktop validation.
