# Install and update WizZ Desktop

Download the current stable version from [GitHub Releases](https://github.com/yvvvl/WizzController/releases/latest).
Windows 10/11 x64 and Ubuntu-compatible Linux desktops on x64 or ARM64 are
supported. macOS remains experimental; there is no supported macOS download.
Your computer and WiZ lights should be on the same local network.

## Windows

- The `windows-x64-setup.exe` asset installs WizZ Desktop. The installer and
  executable are not digitally signed yet, so Windows may show SmartScreen.
  Check that the download came from this repository before running it.
- Alternatively, extract the entire `windows-x64.zip` asset and run
  `WizZDesktop.exe`. Keep `_internal` beside the executable; do not run it
  inside the ZIP. The portable ZIP has a matching `.sha256` sidecar.
- On supported portable installations, **Settings → Check for updates →
  Install and restart** downloads and installs a stable update from
  inside the app. Back up your configuration before a major change.

To check the portable ZIP, run `Get-FileHash` on the downloaded file in
PowerShell and compare its SHA-256 value with the adjacent `.sha256` asset.
The setup executable currently has no separate `.sha256` asset.

## Linux (x64 and ARM64)

Choose `linux-x64.tar.gz` for Intel/AMD or `linux-arm64.tar.gz` for 64-bit
ARM. Verify the matching `.sha256` asset, extract the archive, and run
`./install.sh` inside the extracted directory. Installation is per-user and
does not require `sudo`. Open **WizZ Desktop** from the applications menu and
optionally pin it to the dock. Settings and logs are preserved when the app is
updated or uninstalled.

The installed app can update through **Settings → Check for updates → Install
and restart**. Running `./WizZDesktop` directly from the extracted
directory is also possible, but it is not the managed installed layout.

To uninstall the per-user copy, run
`~/.local/share/WizZDesktop/uninstall.sh`. This removes the app and launcher,
not your configuration or logs.

On Wayland, WizZ Desktop prefers XWayland when Qt's XCB libraries are
available, enabling Quick Panel placement and edge snapping. If startup
reports missing libraries, install `libxcb-cursor0`, `libxcb-icccm4`, and
`libxcb-keysyms1`. A forced Wayland backend leaves window placement to the
compositor. The tray requires an AppIndicator-compatible desktop. Without a
tray, the main window remains usable. Global hotkeys are not available on
Linux yet; do not run the app as root to work around this.

## Checksum and saved data

Use `sha256sum -c <archive>.sha256` on Linux or compare `Get-FileHash` with
the sidecar on Windows. Only execute packages from the official release page.

| Installation | Settings and logs |
| --- | --- |
| Windows | `%LOCALAPPDATA%\WizZDesktop\config` and `%LOCALAPPDATA%\WizZDesktop\logs` |
| Linux | `~/.config/WizZDesktop/config` and `~/.local/state/WizZDesktop/logs` |

You can open the actual locations through **Settings → About → Data/Logs**.
Older Flet installations are migrated when needed. Local JSON may contain IP
addresses, MAC addresses, and preferences; do not share it in issue reports.
