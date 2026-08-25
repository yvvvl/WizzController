# ADR 0004: Cross-platform desktop architecture

- Status: Accepted
- Date: 2026-07-26
- Scope: Desktop platform integration, packaging and validation
- Product targets: Windows stable, Linux beta, macOS experimental

## Context

WizZ Desktop already has a substantially portable application core, but its
desktop integration was designed and validated primarily for Windows. Before
continuing with Effects Engine work, the platform boundary needs to be made
explicit so that Linux and macOS support can grow without duplicating the
application or weakening the stable Windows experience.

The current repository contains three different kinds of code:

1. platform-neutral WiZ and application logic;
2. desktop concepts that are portable but currently depend on Windows
   helpers;
3. genuinely platform-specific implementations.

Treating all three as one layer would either spread `os.name` checks through
the product or encourage per-OS forks. Neither is acceptable.

The target support levels are deliberately different:

- **Windows stable:** the existing supported product and release gate;
- **Linux beta:** a native desktop build with documented desktop-environment
  limitations and graceful feature degradation;
- **macOS experimental:** buildable and testable in CI, with real-machine or
  community validation required before a stronger support promise.

This ADR defines contracts and ownership only. It does not authorize
production code, dependency, UI, workflow or packaging changes.

## Current platform assessment

### Already platform-neutral

The following responsibilities use Python, Flet or network interfaces without
depending on a specific desktop OS:

- `LightController`, including command ownership, device state and discovery
  orchestration;
- `WizProtocol`, including UDP transport and network-interface discovery;
- the optional `pywizlight` adapter and WiZ capability parsing;
- action sequences, favorites and most configuration models;
- localization and the main Flet control tree;
- Quick Panel state, snapshots and WiZ actions;
- filesystem paths derived from Flet application storage in packaged mode.

Platform support must not change the contracts or ownership of
`LightController` or `WizProtocol`.

### Windows-only today

The following behavior has a direct Win32 or Windows packaging dependency:

- native global hotkeys through `RegisterHotKey`;
- start-at-login registration through
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`;
- restoring and focusing an existing window through Win32 window APIs;
- Quick Panel work-area and monitor positioning through `user32`;
- second-instance activation and controlled takeover through named Windows
  mutexes and events;
- packaged executable discovery and Windows-specific process inspection;
- the release build script and current packaged artifact.

The settings label and API named “Start with Windows” also expose the current
implementation instead of the product-level concept “Start at login”.

### Partially portable or capability-dependent

- **Global hotkeys:** the `keyboard` fallback can run outside Windows, but its
  own documentation describes Linux root/device requirements and experimental
  OS X support. It is not a sufficient production contract for Linux or
  macOS, and the upstream repository is archived.
- **Tray:** `pystray` has Windows, macOS and several Linux backends, but backend
  features differ. Linux behavior varies between AppIndicator, GTK and Xorg;
  default activation is not universally supported. macOS also does not
  provide the same default-action behavior and has main-thread/run-loop
  constraints.
- **Single instance:** Unix-like systems currently use a file lock, but do not
  signal the first instance to restore its window. Failure to create the lock
  currently fails open for development, which is not a production guarantee.
- **Quick Panel:** its state and actions are portable, while compact-window
  placement, frameless behavior, always-on-top, taskbar visibility and focus
  are window-system capabilities. The current work-area implementation is
  Windows-only.
- **Open data folder:** Windows uses `os.startfile`; other platforms only
  display the path.
- **UI window lifecycle:** Flet exposes common window properties, but desktop
  environments and window managers do not promise identical positioning,
  focus or tray semantics.

## Decision

WizZ Desktop will remain one application and one source tree. Platform support
will be implemented in future phases through small platform-service contracts
selected once at the application composition root.

```text
Application / Flet UI / Quick Panel intent
                    |
          Desktop service contracts
                    |
     +--------------+--------------+
     |              |              |
 Windows adapters  Linux adapters  macOS adapters

LightController -> WizProtocol -> WiZ devices
        (outside the desktop platform boundary)
```

No feature, screen or WiZ control path will be forked by OS. Platform adapters
may differ, as packaging necessarily does, but the product behavior and domain
model remain shared.

### Desktop capability model

A future immutable `DesktopCapabilities` snapshot will describe effective
runtime support. It is a discovery result, not a table keyed only by operating
system. At minimum it must represent:

- global hotkey registration;
- interactive hotkey recording;
- tray/menu-bar availability;
- tray default-action availability;
- start-at-login availability and permission state;
- window show, hide, restore and focus;
- reliable work-area positioning;
- frameless, always-on-top and taskbar-skip behavior;
- single-instance exclusion and activation;
- opening a folder with the system file manager.

Capabilities may be available, unavailable, degraded or permission-dependent,
with a user-facing reason. This is necessary because Linux behavior depends on
the active desktop session and tray backend, while macOS behavior may depend
on user permissions.

The UI consumes capabilities; it does not infer them from `os.name`,
`sys.platform` or a product version. Future direct platform checks belong only
in adapter discovery and bootstrap code.

### Platform service contracts

The future platform boundary will consist of focused services rather than one
large platform manager:

- **`HotkeyService`:** register, unregister and optionally record shortcuts;
  expose conflicts, permission state and backend availability.
- **`TrayService` / `TrayBackend`:** own native icon lifecycle and menu
  integration. Menu definitions and application actions remain shared.
- **`AutostartService`:** expose the generic `start_at_login` setting and
  status. Windows Registry, Linux XDG Autostart and macOS ServiceManagement
  are adapter details.
- **`WindowService`:** show, hide, restore, focus, query a work area and
  perform optional positioning. The generic implementation may use Flet;
  native helpers remain behind an adapter.
- **`SingleInstanceService`:** guarantee exclusion and, where supported,
  activation of the owning instance. Unix support requires an explicit IPC
  decision in addition to file locking.
- **`SystemIntegrationService`:** open folders and other small shell
  integrations that do not justify domain dependencies.

The exact Python interfaces and module layout are deferred. These names
describe responsibilities, not approved implementation classes.

### Hotkeys

Hotkeys are optional desktop input, never a prerequisite for WiZ control.
When no safe backend is available:

- the application remains fully usable through its UI and tray menu;
- shortcut settings report that registration or recording is unavailable;
- startup does not fail;
- configured shortcuts remain stored so that another supported environment
  may use them.

The future Linux and macOS backend selection requires a separate technical
spike. The current `keyboard` package must not be treated as the production
cross-platform answer, and no replacement library is selected by this ADR.

### Tray and application lifecycle

The tray/menu-bar integration must use explicit menu commands as its portable
baseline. Primary click, double click or “default” actions are enhancements
only when the active backend advertises them.

If the tray is unavailable:

- closing the main window closes the application normally;
- “close to tray” and “start minimized to tray” are hidden or disabled with a
  reason;
- Quick Panel remains reachable from the main UI if its window capabilities
  are available.

The tray adapter is responsible for satisfying native run-loop requirements.
This is particularly important on macOS and for Linux GTK/AppIndicator
backends.

### Autostart

The product setting becomes the platform-neutral concept “Start at login”.
Its future adapters are:

- Windows: current per-user Registry registration;
- Linux: an XDG autostart desktop entry associated with the installed
  application;
- macOS: Apple ServiceManagement registration inside a valid application
  bundle.

Autostart is installation-specific. It must not assume that a development
command, unpacked artifact or unsigned bundle has the same executable identity
as an installed release. Unsupported or permission-blocked states are
reported instead of silently changing user preference.

### Application windows and Quick Panel

The full main window is the portable baseline. Quick Panel is split into:

- portable content, state and actions;
- optional compact-window presentation;
- optional monitor/work-area placement;
- optional tray activation.

When compact positioning, frameless presentation, focus or always-on-top
cannot be provided reliably, the fallback is a normal decorated WizZ window
showing the same controls. A desktop integration failure must never create a
second WiZ controller or bypass `LightController`.

Linux Wayland, Linux X11 and macOS must be validated separately because
window placement and focus policies differ. Linux beta does not promise exact
Windows Quick Panel geometry on every compositor.

### Packaging

Packaging is platform-specific output from one source tree:

- a shared verification phase runs before every package build;
- Windows, Linux and macOS use small target-specific build scripts or CI jobs;
- dependencies and metadata may be selected per target without branching the
  application;
- artifacts always identify OS and architecture;
- signing, notarization and installer formats are release concerns layered on
  top of a successful native build.

The current Windows packaging path remains the stable release path.

Linux package format, desktop integration metadata and x64/arm64 coverage are
deferred until the first native build spike. macOS signing and notarization
are also deferred; an unsigned/internal artifact may support early
experimental validation, but is not a public stable release.

### Validation environments

Each available environment has a distinct role:

| Environment | Validates | Does not establish |
| --- | --- | --- |
| Real Windows | Stable desktop behavior, tray, hotkeys, autostart, Quick Panel, package and real WiZ LAN | Linux or macOS behavior |
| Ubuntu Server | Headless core, protocol simulations, configuration and unit/contract tests | Linux desktop integration |
| WSL | Development tests and a Linux build experiment | Representative tray, Wayland/X11, autostart, hotkeys, focus or LAN discovery |
| Ubuntu Desktop VM | Linux package, X11/Wayland desktop behavior and graceful degradation | All distributions, compositors or physical hotkey devices |
| macOS CI runner | Compilation, tests and native package production | Interactive menu-bar behavior, permissions, local LAN or human UX |
| Real/community Mac | Launch, menu bar, windows, permissions, autostart and LAN smoke tests | Stable support until coverage is repeatable |

Hardware-free simulators and contract tests remain the first validation layer.
Real WiZ devices are required only for LAN and device behavior, not for
desktop adapter contracts.

## Platform acceptance levels

### Windows stable

- current control behavior and desktop integrations do not regress;
- the signed/release packaging path remains reproducible;
- tray, hotkeys, start-at-login, single-instance activation and Quick Panel
  pass native smoke tests;
- full automated tests pass.

### Linux beta

- the shared core and main Flet UI pass on native Linux;
- a reproducible native artifact launches on Ubuntu Desktop;
- X11 and Wayland behavior is documented separately;
- unavailable tray, hotkey, autostart or compact-window capabilities degrade
  safely;
- second-instance exclusion cannot fail open silently;
- local WiZ discovery/control is smoke-tested on a real Linux LAN before beta.

### macOS experimental

- tests and a native macOS artifact are produced on a macOS CI runner;
- unsupported capabilities are reported without blocking the main UI;
- at least one real or community Mac validates launch, menu-bar lifecycle,
  window behavior, required permissions and local WiZ networking;
- signing/notarization and broad architecture coverage are not implied.

## Explicitly rejected

- OS-specific forks, long-lived platform branches or duplicated applications.
- Importing Windows helpers from the portable WiZ core.
- Changing `LightController` or `WizProtocol` to solve desktop integration.
- Treating Flet property availability as proof of identical OS behavior.
- Treating `keyboard` as a verified Linux/macOS production backend.
- Assuming every Linux desktop has a compatible tray.
- Depending on tray primary-click behavior for essential navigation.
- Calling Ubuntu Server or WSL a Linux desktop acceptance environment.
- Calling a successful macOS CI build real-hardware or UX validation.
- Enabling “close to tray” when no operational tray is present.
- Promising exact Quick Panel placement on every window manager/compositor.
- Building a single monolithic platform service with unrelated concerns.

## Consequences

Positive:

- WiZ control and future Effects Engine work remain portable by construction;
- stable Windows behavior can be preserved while other platforms mature;
- integrations fail as optional capabilities rather than taking down the app;
- adapter contracts can be simulated and tested without each physical OS;
- packaging differences do not become product forks.

Costs:

- desktop capabilities and fallback states need explicit UI treatment;
- Linux requires validation across at least Wayland and X11;
- macOS needs real-machine or community testing beyond CI;
- current Windows-specific responsibilities must eventually move behind
  contracts;
- package metadata, dependencies and native permissions require per-target
  maintenance.

## Deferred implementation sequence

1. Freeze contract tests for current Windows behavior.
2. Introduce capability and platform-service contracts with fakes; preserve
   current Windows adapters unchanged behind them.
3. Remove platform checks from consumers and add graceful UI fallbacks.
4. Add a Linux native build and Ubuntu Desktop smoke matrix.
5. Spike Linux tray, hotkey, autostart, window and single-instance adapters.
6. Add macOS CI build/test packaging.
7. Validate macOS desktop behavior with a real machine or community testers.
8. Decide package formats, signing, notarization and architecture coverage in
   separate release ADRs.

Each step is a separate implementation phase. None is part of this
documentation change.

## Sources reviewed

- [Flet publishing and native build matrix](https://flet.dev/docs/publish/)
- [pystray usage and backend limitations](https://pystray.readthedocs.io/en/latest/usage.html)
- [pystray platform FAQ](https://pystray.readthedocs.io/en/latest/faq.html)
- [`keyboard` supported systems and limitations](https://github.com/boppreh/keyboard)
- [XDG Autostart specification](https://specifications.freedesktop.org/autostart/0.5/)
- [Apple Service Management](https://developer.apple.com/documentation/servicemanagement/)
- [GitHub-hosted runner platforms](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
