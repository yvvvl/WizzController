# v1.2.0 Windows release candidate artifact

Status: Ready for owner approval

Date: 2026-08-28

## Candidate

- Product: WizZ Desktop
- Version: `1.2.0`
- Build: `2`
- Commit: `b081e2cd163d`
- Platform: Windows x64

## Local release material

- ZIP: `dist/release/WizZDesktop-v1.2.0-windows-x64.zip`
- SHA-256: `ae0489f14d010f4f5ab4ecfd8d9c1a6132fca0e364dfb2af62192605d1ee0ed6`
- Manifest: `dist/windows/BUILD_INFO.json`

## Evidence

- The release build logged `v1.2.0 (build 2)` on launch.
- It used `%LOCALAPPDATA%\\WizZDesktop` for config and logs.
- It detected the existing saved WiZ light.
- Its second execution exited successfully while the primary process remained
  active.
- The ZIP includes its executable, `BUILD_INFO.json`, third-party notices and
  licenses.
- ZIP inspection found no real configuration, device, hotkey or log files.

## Scope statement for public release notes

v1.2.0 improves Windows reliability, temporary multi-light selection,
persistence and manual update discovery. It does **not** provide RGBIC stable
support, Screen Sync, streaming, automatic installation or an active Quick
Panel.

## Publication boundary

The artifact is ready locally only. Creating `v1.2.0`, merging into `main`,
or publishing a GitHub Release requires explicit owner approval.
