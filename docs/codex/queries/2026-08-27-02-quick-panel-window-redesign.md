# Quick Panel window redesign

Date: 2026-08-27  
Status: Design approved, implementation pending

## Goal

Replace the current same-window mode switch with a compact temporary window
that can be opened from the tray without moving or resizing the main window.

## Required behavior

- The Quick Panel is a separate, frameless, always-on-top utility window.
- It opens above the taskbar at the lower-right of the active work area.
- It contains only fast actions: target, power, brightness, color/white mode
  and a short favorites list.
- Clicking outside the panel hides it.
- Losing focus hides it.
- Closing the panel never stops WizZ or the main window.
- Tray activation toggles the panel; an explicit “Open full window” action
  restores/focuses the main application.
- The panel and main window share state through the existing controller; no
  duplicate WiZ transport or LightController is created.

## Constraints

- Preserve all existing actions and translations.
- Keep Windows behavior stable while the new window lifecycle is validated.
- Provide a safe fallback when a platform cannot create a second window.
- Do not modify `LightController` or `WizProtocol`.

## Implementation sequence

1. Identify the supported Flet second-window mechanism for version 0.85.2.
2. Add a window-service contract for temporary utility windows.
3. Implement a fake lifecycle and focus-loss tests first.
4. Implement the Windows adapter behind an opt-in flag.
5. Validate open, outside-click hide, focus-loss hide and full-window restore.
6. Only then connect the tray action and remove the same-window mode switch.
