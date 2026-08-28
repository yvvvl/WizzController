# Home targeting and DEV virtual bulbs

Status: Completed with a documented DEV-only visual limitation

Date: 2026-08-27

Related roadmap: `docs/codex/plans/2026-08-27-v1.2-public-release-and-rgbic-beta-roadmap.md`, Phase B.

## Objective

Make the Home destination selector communicate one, partial and all-light
selection clearly, then provide a safe development fixture for exercising the
same controller contract without multiple physical WiZ bulbs.

## Delivered

- The Home selector preserves and displays `single`, `selected` and `all`
  targeting, including a concise selected-count label.
- Partial selections are restored from `selected_ips`; selecting every saved
  light maps to `all` without creating a persistent group.
- A source-run-only `WIZZ_DEV_VIRTUAL_BULBS=<count>` mode creates one to
  twelve virtual RGBTW bulbs using `VirtualLightController`.
- The simulator has no UDP endpoint, no discovery task and does not persist
  its bulbs or target choices into the user's WiZ configuration.
- The Home-only DEV preview displays virtual bulb state, selection, brightness
  and representative static/dynamic scene colours.

## Known limitation

The simulator is valid for deterministic selection, targeting, static colour,
brightness, power, favorites and scene-command tests. On Flet 0.85.2, visual
delivery of continuous background scene frames can be irregular in a running
desktop client: a later user interaction may reveal the latest frame. This is
not evidence about real WiZ dynamic scenes and is not used as release
validation for fades. It remains a DEV-only fixture and is excluded from the
public packaged build.

## Validation executed

- `python -m pytest -q`: 356 passed, 98 existing deprecation warnings.
- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`: exit 0.
- `python tools/i18n_audit.py`: 590 keys in English and Spanish; no potential
  hardcoded UI strings.
- `git diff --check`: clean.

## Next step

Phase C: integrate the already-tested read-only GitHub release client into a
failure-safe Settings UI. It must only show availability and open the official
release page; it must not download, install or replace the application.
