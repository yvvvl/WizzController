# Remove Quick Panel from v1.2 active desktop flow

Status: Completed

Date: 2026-08-28

## Decision

The Quick Panel is removed from the active v1.2.0 desktop composition. It was
visually and behaviorally unreliable as a reused native Flet window: tray
activation could restore the compact layout instead of the main application.

## Implemented boundary

- `main.py` no longer constructs `QuickPanelController` or `QuickPanelView`.
- WiZ state callbacks now update only the visible main application.
- `TrayService` receives no Quick Panel callbacks in the public composition.
- The primary tray action now restores the main window immediately on Windows,
  Linux and other supported systems.
- The Quick Panel menu actions are absent from the public tray menu.

The experimental controller and view are deliberately retained in source and
their tests remain intact. They are not reachable from the shipped app and can
only return through a separate, validated design decision.

## Validation

- Tray restore, historical Quick Panel isolation and instance-activation tests:
  48 passed.
- Python compilation and whitespace validation completed without errors.

## Follow-up

Continue Phase D Windows release hardening using the simpler one-window tray
flow. Do not include Quick Panel behavior in the v1.2.0 release checklist.
