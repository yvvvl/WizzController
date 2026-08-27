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
- The first Wayland manual probe showed a visible icon with no menu response.
  The adapter now prefers pystray's `run_detached()` when available so GTK
  owns its event loop; interactive validation remains pending.
- Added tests for Wayland permission degradation, autostart, folder opening and
  independent window capabilities.
- Added a CI smoke matrix for Ubuntu and Windows that compiles and tests
  the platform boundary without starting the desktop application.

## Deliberate limitations

- The new services are not wired into `main.py` yet.
- No Linux tray backend is enabled in the product runtime.
- Global hotkeys remain capability-reported as degraded on X11 and permission
  required on Wayland; no backend replacement was introduced.
- Single-instance activation is explicitly unavailable until a portable
  activation mechanism is designed.
- No Linux package or macOS backend is produced in this phase. macOS support is
  currently deferred because no real validation environment is available.

## Decisions preserved

- `LightController` and `WizProtocol` remain unchanged.
- There are no operating-system forks of the WiZ core.
- Capability states are explicit instead of silently pretending support.
- Tests do not access hardware or the network.

## Validation

Focused platform tests: 28 passed locally.

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

### Tray smoke validation (2026-08-27)

On Ubuntu 22.04 GNOME/Wayland with `PYSTRAY_BACKEND=appindicator`, a direct
pystray smoke test using `icon.run()` on the main thread produced a visible
indicator and an interactive menu. The `Cerrar prueba` action stopped the
icon successfully. This validates the desktop/AppIndicator installation.

The WizZ `LinuxTrayBackend` remains intentionally unwired and requires a
separate run-loop integration design before product use; its lifecycle tests
are not evidence of visual desktop integration.

A follow-up smoke test exercised `LinuxTrayBackend.run_foreground()` directly
with the AppIndicator backend. The icon appeared in GNOME's indicator area,
the menu was interactive, and `Cerrar prueba` stopped the loop. Process
inspection after closing showed no remaining WizZ process. GNOME may keep the
indicator overflow menu open until it is dismissed, but the backend itself was
stopped.

### Hotkey strategy decision (2026-08-27)

The Ubuntu validation session is GNOME on Wayland. Capability detection
therefore reports global registration and recording as
`permission_required`, rather than claiming that the existing Windows
implementation is portable. Wayland hotkeys remain an optional capability:
the application must continue to work through its UI and tray when permission
or a safe backend is unavailable. X11 may be reported as degraded until a
backend and permission model are validated on a real desktop session.

No replacement hotkey library is selected in this phase. A future spike must
evaluate registration, recording, conflict handling and user-facing recovery
separately for X11, Wayland and macOS.

### Autostart and folder integration validation (2026-08-27)

The Linux autostart service was exercised with a temporary configuration
directory: `is_enabled()` started false, enabling returned true and created the
entry, and disabling returned true and removed it. No user autostart
configuration was changed.

The system integration service reported `open_folder: available`; opening the
home directory returned true and launched the file manager, while a nonexistent
path correctly returned false.

## Next steps

1. Design and test a main-thread tray run-loop bridge for the WizZ adapter.
2. Validate the hotkey permission and messaging flow on representative X11 and
   Wayland sessions.
3. Keep CI focused on Windows and Linux until macOS validation is available.
4. Design the tray run-loop bridge and only then consider service wiring.
