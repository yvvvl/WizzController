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

Focused platform tests: 25 passed locally.

Full-suite validation is required before merging.

## Next steps

1. Add a Linux tray adapter with an injectable menu/action boundary.
2. Decide the X11/Wayland hotkey strategy and permission messaging.
3. Add Linux/macOS CI smoke jobs.
4. Wire services only after manual Linux desktop validation.
