# Develop and validate WizZ Desktop

The supported desktop entry point is `python -m qt_ui.run`. Use Python
3.11–3.13; the Linux build pipeline uses Python 3.12. Do not test against a
real bulb when virtual-light mode is intended.

## Set up from source

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m qt_ui.run
```

Linux (use a Python 3.12 interpreter, even on distributions whose default is
newer):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-qt-linux.txt -r requirements-dev.txt
PYTHONPATH="$PWD" .venv/bin/python -m qt_ui.run
```

The Linux desktop also needs system Qt/XCB and AppIndicator libraries. The
current package list is in the `build-linux` job of
[the official release workflow](../.github/workflows/build-windows.yml).
macOS source/build support is experimental and is not a public release target.

## Virtual lights and tests

Source builds accept `WIZZ_DEV_VIRTUAL_BULBS=3`. This starts three simulated
lights, uses a separate test profile, and sends **no WiZ LAN traffic**.
Packaged public builds ignore the flag. You can test multi-light targeting,
brightness, RGB, white temperature, scenes, routine steps, and schedules
without owning multiple bulbs.

```powershell
$env:WIZZ_DEV_VIRTUAL_BULBS = "3"
try { .\.venv\Scripts\python.exe -m qt_ui.run }
finally { Remove-Item Env:WIZZ_DEV_VIRTUAL_BULBS }
```

```bash
WIZZ_DEV_VIRTUAL_BULBS=3 PYTHONPATH="$PWD" .venv/bin/python -m qt_ui.run
```

Run validation before proposing changes:

```bash
python -m compileall -q main.py app_meta.py core config qt_ui localization tests tools
python -m pytest -q
python tools/i18n_audit.py
git diff --check
```

On Windows, `scripts/verify_repo.ps1` provides a local shortcut. See the
[manual release checklist](release-validation.md) for real-device, desktop,
and packaged-update checks. Automated tests do not replace those checks.
The [contribution guide](../CONTRIBUTING.md) and
[repository policy](repository-maintenance.md) explain code ownership, safe
cleanup, and the files that must remain local.

## Current and legacy paths

| Path | Role |
| --- | --- |
| `qt_ui/` | Supported Qt/PySide6 interface, Quick Panel, and runtime. |
| `core/`, `config/`, `localization/` | Control, persistence, platform services, and language resources. |
| `scripts/build_qt_windows.ps1`, `scripts/build_qt_linux.sh` | Official Windows/Linux release builds. |
| `.github/workflows/build-windows.yml` | Official three-platform release pipeline and tag publisher. |
| `scripts/build_qt_macos.sh` | Experimental unsigned Mac smoke build only. |
| `ui/`, `main.py`'s `run_flet_legacy()` | Retained Flet source for migration/historical tests; not a supported user UI. `python main.py` dispatches to Qt. |
| `scripts/build_windows.ps1`, `scripts/build_linux.sh` | Retired Flet build paths; do not use for a public release. |

Flet is an optional `legacy-flet` dependency in `pyproject.toml` and is
installed by the development requirements for historical tests. It is not
bundled in Qt releases. Do not delete the legacy code or its tests until
migration coverage and dependencies are explicitly reviewed.

The active architecture is:

```text
Qt UI / desktop runtime
        ↓
application services and action sequences
        ↓
WiZ LAN control + persistent JSON configuration
```

## Build an official-format local package

Windows (Inno Setup 6 or 7 is needed for the setup executable):

```powershell
.\scripts\build_qt_windows.ps1 -Clean
.\scripts\test_windows_build.ps1 -LaunchSecondInstance
```

Linux (after system prerequisites and `requirements-build.txt`):

```bash
bash scripts/build_qt_linux.sh --clean
```

Both builders write distributable files to `dist/release/`. A source run or
a self-built package is not a substitute for testing the published archive.
