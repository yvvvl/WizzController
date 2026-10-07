# Local routine schedules

WizZ Desktop can run an existing routine at a chosen local time on selected
weekdays. This works on Windows and Linux without a cloud account or an
external scheduling service. The application process must stay running; it can
remain in the system tray. A scheduled run is skipped if the computer is off,
asleep, or WizZ is not running at the scheduled minute. Missed runs are **not**
replayed on wake/startup, to avoid an unexpected light change.
To have schedules available after sign-in, enable start-at-login in **Settings**
and keep the tray enabled.

## Use

1. Create or inspect a routine in **Routines**. A routine may give individual
   steps explicit bulb or group targets.
2. Scroll to **Local schedules** and choose **New schedule**.
3. Select a routine, a 24-hour local time (`HH:MM`), at least one weekday, and
   a default destination (all discovered lights, one bulb, or a saved group).
   Explicit targets on routine steps take priority over the schedule target.
   Scheduled routines accept direct light steps, waits and nested routines.
   Steps that depend on the changing UI selection or arbitrary methods
   (favorites, custom scenes, conditions, target-mode changes, custom methods)
   are rejected for scheduling rather than potentially affecting wrong lights.
   They remain usable when the routine is run manually.
4. Save. The schedule can subsequently be edited, paused/resumed, or deleted.
   The row shows the last result. Deleting a routine disables its schedules.

The clock and time zone are those of the computer running WizZ, not of a phone
or light bulb. Weekdays use Monday=0 internally. When daylight saving time
repeats a wall-clock minute, an occurrence is run only once; a wall-clock
minute that does not exist is skipped. Changing the computer's date/time may
change when future schedules are due, but does not replay a recorded occurrence.

## Reliability and privacy

- `config/routine_schedules.json` (under the normal persistent app config
  directory in a packaged build) is versioned and written by atomic replacement.
  Unknown versions or corrupt data are preserved and scheduling is disabled
  with an error shown in the UI; the rest of WizZ continues to work.
- At the beginning of the matching minute, WizZ records an occurrence *before*
  dispatching its light commands. Thus a restart during that minute cannot
  trigger a duplicate. If the process crashes after recording but before
  execution finishes, that occurrence may be missed. This is an intentional
  at-most-once policy, not a guarantee of delivery.
- A 15-second in-process timer checks due schedules. Sequence execution runs
  outside the UI thread; the existing sequence lock prevents routines from
  interleaving. This is not a real-time timer: OS scheduling delays may move a
  run by seconds. The app does not ask the OS to wake a sleeping computer.
- All scheduling metadata stays on the device. The normal WiZ LAN command path
  is used. An unavailable target is reported as a failed run instead of success.
  Light acknowledgements are outside the scheduler's guarantee; a successful
  result means the routine commands were accepted by the local controller.
- A schedule never uses the UI's changing "current selection" as its default
  target. Existing per-step targets still work. Saved group destinations are
  resolved at run time, so editing a group updates subsequent runs.

## Testing

Run `python -m pytest -q tests/test_local_routine_scheduler.py
tests/test_update_installer.py` in the project's environment. The tests cover
weekdays, restart deduplication, DST fall-back, invalid data, failed writes,
target inheritance and the updater's UTF-8 BOM.

For a visual dry run without contacting physical lights, run WizZ with
`WIZZ_DEV_VIRTUAL_BULBS=3`, create a schedule for the next local minute, and
leave the app running. Verify that the result updates once, including if you
reopen WizZ within that minute. Repeat with a paused schedule and with a
nonexistent/offline target. Do not use virtual mode to verify actual LAN
delivery; that requires a real bulb.

The detached Windows updater progress script is encoded as UTF-8 **with BOM**
so Windows PowerShell 5.1 displays Spanish accents correctly. Its title,
initial status and later statuses follow the saved application language.
