# ADR 0001: Role of pywizlight in WizZ Desktop

- **Status:** Accepted for v1.1 implementation
- **Date:** 2026-07-23
- **Decision owners:** WizZ Desktop maintainers

## Context

WizZ Desktop currently combines native WiZ UDP control with `pywizlight==0.6.3`.

Native UDP gives the application low-latency fire-and-forget control. `pywizlight` provides maintained WiZ compatibility logic, discovery, capability interpretation, firmware fallbacks, supported-scene data and RGB/CW conversion.

The repository previously described `pywizlight` as optional in some comments, while `core/wiz_color.py` imports it directly. That contradiction makes startup, packaging and licensing behavior unclear.

## Decision

`pywizlight` is a **required runtime dependency** for WizZ Desktop v1.1.

It is used only behind `core/pywizlight_adapter.py` for:

- complementary discovery;
- read-only capability resolution;
- firmware compatibility;
- per-device Kelvin ranges;
- supported scenes;
- RGB/CW conversion.

Native WizZ Desktop UDP remains responsible for:

- power;
- brightness;
- RGB;
- Kelvin;
- scenes;
- slider and picker updates;
- hotkeys;
- routines;
- favorites;
- tray actions.

## Boundary

After refactoring:

- only `core/pywizlight_adapter.py` imports `pywizlight`;
- UI modules never import it;
- `LightController` consumes WizZ-owned dataclasses;
- upstream classes do not cross the adapter boundary;
- capability reads are asynchronous, time-limited and cached;
- no capability read occurs in an action hot path.

## Why not remove the dependency?

Removing it would require maintaining duplicated discovery, legacy-firmware logic, capability classification and color-channel conversion. That increases compatibility and licensing risk for negligible package-size savings.

## Why not use it for all control?

Its request layer can resend UDP datagrams until a response is received. This improves reliable reads but is unsuitable for high-frequency pointer and slider events.

## Consequences

### Positive

- broader hardware compatibility;
- less duplicated protocol knowledge;
- clear packaging and attribution;
- low-latency native control is preserved;
- future upstream improvements can be evaluated independently.

### Negative

- the package is mandatory;
- its exact version must be tested and pinned;
- its MIT notice must ship with releases;
- adapter compatibility tests are required.

## Upgrade policy

Upgrades are isolated commits. Before changing the pin:

1. compare source and public API;
2. run all tests and capability fixtures;
3. run the physical WiZ color probe;
4. test discovery, Kelvin, RGB and scenes;
5. build and open the Windows package;
6. verify the embedded package and license;
7. allow a one-commit revert.
