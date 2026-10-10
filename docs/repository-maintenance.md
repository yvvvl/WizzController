# Repository boundaries and cleanup

This repository contains **source**, small test fixtures, documentation,
license notices, and assets needed to build WizZ Desktop. It does not need
your installed app, personal settings, build output, downloaded releases, or
logs. `.gitignore` protects common local paths, and
`tools/repository_hygiene.py` checks tracked paths in CI. Neither mechanism
removes a file that was already committed or substitutes for reviewing a diff.

| Keep in Git | Keep only on your computer |
| --- | --- |
| `qt_ui/`, `core/`, `config/*.py`, `localization/` | `config/json/*.json` except `*.example.json` |
| `tests/`, `tools/`, current build/install scripts | `.venv/`, `build/`, `dist/`, `logs/`, `artifacts/` |
| Source assets and their license texts | `.env*` secrets, local IDE settings, bulb IP/MAC exports |
| `pyproject.toml`, requirements files, `uv.lock` | Generated PyInstaller specs, caches, screenshots |

`uv.lock` is intentionally tracked to record a resolved development
environment. Release scripts currently install from platform-specific
requirements files, so updating the lock file alone does **not** change a
release dependency. Review both whenever dependencies change.

## Current code ownership

- `qt_ui/` is the supported interface and desktop runtime.
- `core/` owns light control, platform integration, and reusable services.
- `config/` owns persisted settings and migrations; its JSON examples are
  public templates, while real JSON files may contain private device data.
- `ui/` and `main.py`'s legacy Flet entry are retained for historical tests.
  They are not bundled in Qt releases. Removing them should be a separate
  change after replacing any still-useful coverage.
- `scripts/build_windows.ps1` and `scripts/build_linux.sh` are legacy build
  entry points; official builds use `scripts/build_qt_*`.
- `THIRD_PARTY_NOTICES.md` is the single notice index. License texts live in
  `licenses/` and `assets/fonts/`. Notices do not establish a license for
  the project's own source.

The old Linux beta workflow was removed because its branch no longer exists
and it duplicated official Linux builds on pull requests. Official x64 and
ARM64 builds remain in `.github/workflows/build-windows.yml`. Experimental
macOS smoke runs manually or for relevant PRs targeting `main`.

## Safe cleanup process

Inspect `git status` and `git ls-files` before changing tracked files. Preserve
local untracked/ignored directories even if they look stale: they may contain
someone's tests or configuration. Remove an obsolete tracked file only after
checking references and adjusting tests or documentation. Make a small commit,
run the checks, and verify that release builds still include required assets
and third-party license texts.
