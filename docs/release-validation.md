# Manual release validation

Test the **published package**, not only a source checkout. Download it from
[GitHub Releases](https://github.com/yvvvl/WizzController/releases/latest),
verify the matching `.sha256` for ZIP/tar downloads, extract the entire
archive, and close any other WizZ Desktop instance before starting. Back up
your persistent settings if they matter to you. Record PASS, FAIL, or N/A,
plus expected versus actual behavior for each item.

## Windows and Linux checklist

1. **Install and launch:** use the Windows setup or complete portable ZIP;
   on Linux use the per-user `install.sh`. Check app icon, launcher, tray,
   first launch, single-instance restoration, and clean quit.
2. **Discover and target:** find a real WiZ bulb on the same LAN, add a known
   IP manually, and select one, several, and all bulbs. Confirm no stale
   selection after a light disappears or is removed.
3. **Control:** try power, 20/50/100% brightness, red/green/blue, warm/cool
   Kelvin whites, and several named WiZ scenes. Compare the physical result
   with the UI on single and multi-bulb targets.
4. **Color and favorites:** use the RGB and CCT pickers, exact HEX/Kelvin,
   save and reopen RGB/white favorites, and test recently applied colors.
5. **Routines and schedules:** save, reorder, reopen, and run a multi-step
   routine. Schedule it for the next minute with a fixed bulb/group target;
   verify its last result, pause it, and confirm it does not repeat. Confirm
   a per-step target takes priority over the schedule default. Do not expect
   missed runs to replay after sleep or shutdown.
6. **Quick Panel and interface:** open from the tray, test multi-page bulb
   selection and editable quick actions, drag/snap to each edge and monitor,
   reopen at the remembered position, and test click-outside dismissal.
   Change language/theme, inspect long dropdowns and text clipping, and
   restart to confirm persistence.
7. **Hotkeys:** on Windows, record a non-conflicting chord, compare number-row
   `1` with `Numpad 1` (Num Lock on), use custom RGB/Kelvin actions, and
   confirm one execution per press. On Linux, confirm the UI explains that
   global hotkeys are not operational yet.
8. **Update:** from an older supported installation, use **Settings → Check
   for updates → Install and restart**. Confirm download and
   progress feedback, restart into the expected version, and preservation of
   settings. Do not use a source run as an in-app update test.

The Linux tray requires AppIndicator support. Forced Wayland can limit exact
Quick Panel placement. Screen Sync/Ambilight and audio sync are not included;
mark them N/A. See [installation details](installation.md) and the
[local schedule guide](local-routine-schedules.md) for expected platform
behavior.

## Useful issue report

Include app version, OS and display scale, bulb model/firmware, steps,
expected and actual results, repeatability, and a short screenshot or video.
You can open local logs from **Settings → About → Data/Logs**. Redact IPs,
MACs, tokens, and personal configuration before sharing them. Reports go to
[GitHub Issues](https://github.com/yvvvl/WizzController/issues).
