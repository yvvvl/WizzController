# Safe update notification integration

Status: Completed

Date: 2026-08-28

Related roadmap: `docs/codex/plans/2026-08-27-v1.2-public-release-and-rgbic-beta-roadmap.md`, Phase C.

## Scope

Integrated the existing read-only GitHub Releases client into the Settings
About card. The user explicitly starts the check; it runs outside the UI
thread and reports a recoverable result.

## Behaviour

- Shows the running version and a manual **Check for updates** action.
- Reads stable GitHub Releases only; prereleases remain excluded from the
  public channel.
- Shows current, available, no-release and temporary-service-unavailable
  states without blocking light control.
- Offers **Open release** only for an HTTPS URL under the official
  `github.com/yvvvl/WizzController/releases` path.
- Does not download, install, replace, restart or elevate the application.

## UI correction

The initial card used an expanded Column inside a wrapping Row. Flet 0.85.2
rendered that combination as a grey ErrorWidget. It was replaced with bounded
`ResponsiveRow` columns and verified manually in the desktop app.

## Validation

- Focused update and layout tests pass.
- Manual Windows check confirmed the Settings card renders normally.
- Full project validation is recorded in the release checkpoint commit.

## Next step

Phase D: Windows release hardening: desktop self-test, packaged artifact
inspection, clean-extraction launch, data persistence verification and release
material preparation.
