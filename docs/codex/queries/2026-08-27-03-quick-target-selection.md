# Quick target selection

Date: 2026-08-27  
Status: In Progress

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

## Release scope

This behavior belongs in the public Windows release. RGBIC remains isolated to
the closed beta channel.
