# Linux v1.2.0 beta delivery

Status: In Progress

Date: 2026-08-28

## Objective

Extend the already prepared v1.2.0 Windows candidate with a Linux beta. The
release remains one product and one WiZ core: Windows is stable; Linux is
explicitly beta; macOS stays deferred.

## Existing foundation

- The shared WiZ core, Flet UI, persistence model and automated tests already
  run on Ubuntu Desktop.
- Linux capability contracts, XDG autostart, `xdg-open`, window callbacks and
  a pystray adapter exist under `core/platform`.
- Earlier Ubuntu GNOME/Wayland validation showed that pystray's AppIndicator
  backend provides a visible, interactive tray menu, while another backend can
  expose an inert icon.

## Implementation decisions

- The normal tray service selects `PYSTRAY_BACKEND=appindicator` only on Linux
  GNOME/Ubuntu or Wayland and only when the user did not select another backend.
- Settings uses the platform system service to open data and log folders; the
  Linux fallback is `xdg-open`.
- The existing persisted `startup_with_windows` key is retained for v1.1 data
  compatibility, but on Linux it means start at login and creates/removes the
  user's XDG autostart entry.
- Linux does not claim exact window placement under Wayland. This is governed
  by the compositor, not by the app.
- The existing file-lock single-instance exclusion is retained for beta. It
  prevents duplicate controllers even where foreground activation is not yet
  portable.

## Validation required before release

1. Run the full automated suite on Ubuntu Desktop.
2. Launch the source app on GNOME Wayland and confirm normal UI, tray menu,
   hide/restore and real exit.
3. Confirm Settings > Datos and Logs opens the XDG storage folders.
4. Toggle start at login and inspect the generated desktop entry.
5. Build natively with `flet build linux`, launch the extracted output outside
   the repository and repeat the smoke checks.
6. Perform WiZ discovery and a controlled power/brightness/RGB/Kelvin/scene
   smoke on a Linux LAN when compatible hardware is available.
7. Produce an archive plus SHA-256 only after the above evidence is recorded.

## Out of scope

- New WiZ protocol behavior, RGBIC product support, Screen Sync, streaming or
  scheduler work.
- A Quick Panel, forced window placement, or a Linux promise for global
  hotkeys on Wayland.
- macOS support.
