# Windows candidate: real WiZ validation

Status: Completed

Date: 2026-08-28

Related plan: `docs/codex/plans/2026-08-27-v1.2-public-release-and-rgbic-beta-roadmap.md`, Phase D.

## Scope

Validate the public Windows candidate against an authorized, real WiZ light on
the local network. This was not an RGBIC test and did not use streaming,
Screen Sync or experimental RGBIC payloads.

## Read-only findings

- The device responded to `getPilot`, `getSystemConfig` and `getModelConfig`.
- It reports firmware `1.38.0`, a 2200–6500 K CCT range and RGBTW output.
- The baseline state was captured before any visible command.

## Executed validation

Each command received a successful protocol response and its state was read
back through `getPilot`:

- white: 2700 K at 35%;
- RGB: red at 35%;
- built-in scene: `sceneId` 18;
- final restoration to the original off state, 2200 K and 100% brightness.

The tester visually confirmed the white, red and scene transitions.

## Firmware behavior recorded

A combined restore payload containing `state: false` plus color or scene
parameters returned `Invalid params`. A safe restoration sequence is:

1. apply the desired white/RGB/scene mode and brightness;
2. send the final `state: false` command separately.

This is a hardware-specific protocol observation. It does not justify a
production RGBIC claim and does not change the existing RGBIC architecture.

## Result

The Windows release candidate has real-device evidence for ordinary one-light
power, CCT, RGB and built-in scene control. Remaining Phase D work is desktop
behavior and persistence validation, not basic WiZ protocol reachability.
