# Linux Desktop Integration Phase 1

Date: 2026-08-27  
Status: In Progress

## Objective

Introduce a composition boundary for optional desktop services while keeping
the Windows runtime, UI and WiZ core unchanged.

## Implemented

- Added `core/platform/composition.py` with immutable `PlatformServices`.
- Added `build_platform_services()` to select Linux adapters by capability.
- Unknown platforms return unavailable capabilities instead of silently using a
  Linux or Windows implementation.
- Added deterministic tests for Linux selection and unsupported platforms.

## Deliberate limits

- The composition helper is not wired into `main.py` yet.
- No Windows behavior was moved or replaced.
- No macOS adapter is provided; macOS remains deferred.
- Tray execution still requires the separately validated foreground run-loop.

## Next checklist

1. Run the focused and full test suites on Windows and Ubuntu.
2. Review the composition API and capability fallback behavior.
3. Design the application bootstrap integration without changing existing UI
   behavior.
