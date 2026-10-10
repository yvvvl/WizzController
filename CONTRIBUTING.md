# Contributing to WizZ Desktop

Thank you for helping improve WizZ Desktop. The supported product is the Qt
application in `qt_ui/`. The retired Flet UI is no longer part of the source;
only legacy user-data migration remains in `config/paths.py`.

## Before changing code

- Open an issue for a significant feature or behavior change. Describe the
  user problem, affected platforms, and how it can be tested without a bulb.
- Work on a focused `feature/<topic>` or `fix/<topic>` branch from `main`.
  Do not develop on a release tag or include unrelated cleanup in a bug fix.
- Keep personal bulb configuration, logs, virtual-light screenshots, build
  output, credentials, and local environment files outside Git. The
  [repository policy](docs/repository-maintenance.md) lists what belongs here.
- The project has not selected a project-wide source license. Third-party
  notices do not grant a license to WizZ Desktop's own source.

## Implementation boundaries

- Put desktop interaction and QML presentation in `qt_ui/`, reusable light
  behavior in `core/`, persistence and settings in `config/`, and translated
  user-facing strings in `localization/`. The architecture test prevents
  services from importing the desktop UI.
- Keep device/network work away from the UI thread. Expose a clear result or
  error state so the interface can recover when a bulb is offline.
- Preserve existing JSON configuration. New fields need defaults and a test
  for older saved files; do not require users to delete their settings.
- Cover one bulb, several bulbs, and virtual-light mode where targeting is
  involved. Never let a test contact a real bulb or GitHub unexpectedly.
- State which platforms a feature supports. A green cross-platform smoke
  test is not proof of a real desktop or device interaction.
- Keep dependency declarations and third-party notices in sync when adding or
  upgrading a library. Do not bundle development-only dependencies.

## Validate before a PR

Set up the environment as described in [development.md](docs/development.md),
then run `scripts/verify_repo.ps1` on Windows or the equivalent commands:

```bash
python tools/repository_hygiene.py
python -m ruff check . --select E9,F63,F7,F82
python -m compileall -q main.py app_meta.py core config qt_ui tests tools
python tools/i18n_audit.py --strict
python -m pytest -q
git diff --check
```

This lint selection catches critical errors without pretending the legacy code
is already fully lint-clean. New code should be clearer than this minimum; do
not add blanket lint suppressions just to pass CI. For UI or packaging work,
also follow the [manual release checklist](docs/release-validation.md).

A useful PR explains the behavior change, tests run, affected OSes, screenshots
for visual changes, and any migration or third-party notice changes. Do not
include real IP/MAC addresses or configuration files in reports.
