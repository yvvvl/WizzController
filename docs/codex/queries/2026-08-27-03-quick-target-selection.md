# Quick target selection

Date: 2026-08-27  
Status: Completed

## Decision

WizZ uses a transient multi-target selection instead of requiring users to
create and edit named groups. Home can select any subset of discovered lights;
actions are sent only to that subset. Existing `single` and `all` modes remain
compatible.

## Model

- `single`: one active IP;
- `selected`: two or more selected IPs, persisted as `selected_ips` only as
  the last UI selection;
- `all`: every reachable/saved target.

No duplicate controller or transport is created. The selection is simulated in
tests with multiple targets and validated against the controller's target set.

## Implemented

- `LightController` persists and resolves `single`, `selected` and `all`.
- `TargetSelector` sends a transient subset through the existing controller.
- `tests/test_target_selection.py` covers single, partial and all target sets.
- Commit `93c0136` contains the scoped implementation.

The remaining work is presentation and usability stabilization in Home, not a
missing targeting contract.

## Release scope

This behavior belongs in the public Windows release. RGBIC remains isolated to
the closed beta channel.
