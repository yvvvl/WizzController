# pywizlight integration audit

**Project:** WizZ Desktop  
**Target branch:** `feature/v1.1.0-pywizlight-capabilities`  
**Audit date:** 2026-07-23  
**Scope:** dependency role, runtime boundary, performance, packaging, licensing, and upgrade readiness.

## Executive decision

For WizZ Desktop v1.1, `pywizlight` should be treated as a **required runtime dependency**, but it must not become the latency-sensitive control path.

The architectural split is:

| Responsibility | Owner |
|---|---|
| Frequent `setPilot` operations, sliders, hotkeys, routines, scenes, power, brightness, RGB and Kelvin | WizZ Desktop native UDP |
| Complementary discovery, capability reads, firmware compatibility, supported scenes, Kelvin range and RGB/CW conversion | `pywizlight` behind `core/pywizlight_adapter.py` |

This decision matches the current repository state:

- `requirements.txt` and `pyproject.toml` pin `pywizlight==0.6.3`;
- `core/light_controller.py` invokes `discover_with_pywizlight`;
- `core/pywizlight_adapter.py` uses `pywizlight` discovery and device APIs;
- `core/wiz_color.py` imports `rgb2rgbcw` and `rgbcw2hs` directly.

The adapter currently handles some imports as optional, but the direct color-pipeline import makes the installed package required for normal startup. The implementation and comments must describe that fact consistently.

## Verified upstream facts

### pywizlight 0.6.3

- Released 2025-06-10.
- MIT licensed.
- Author metadata: Stephan Traub.
- Python requirement: `>=3.7`.
- Wheel size: approximately 59.0 kB.
- Source archive size: approximately 43.8 kB.
- Published from source commit `719062be581df04861d41bba0bbd5b38b40f8f87`.

The public API documents:

- UDP discovery;
- `get_bulbtype()`;
- brightness, color, color-temperature and effect features;
- per-device Kelvin range;
- `getSystemConfig`, `getUserConfig`, `getPilot` and `setPilot`;
- smart-plug power reads.

### Latest researched release: 0.6.5

- Released 2026-07-08.
- MIT licensed.
- Python requirement: `>=3.11`.
- Wheel size: approximately 62.1 kB.
- Source archive size: approximately 47.0 kB.
- Published from source commit `0489ad120fa7d6c1d92fd407e5db25d3944f112e`.

The size difference is negligible compared with the Flet/Flutter runtime. Package size is not a reason to duplicate the library.

## Network and latency behavior

`pywizlight` uses asynchronous UDP, but its request path can resend datagrams until a response arrives. That is appropriate for discovery and capability reads; it is not appropriate for every pointer movement or slider tick.

WizZ Desktop must preserve native fire-and-forget UDP for the hot path.

No `pywizlight` network call may occur inside:

- Color Studio drag events;
- brightness slider events;
- hotkey callbacks;
- tray callbacks;
- `ActionSequenceExecutor` action dispatch;
- normal repaint or sync methods.

## Current dependency classification

| Area | Current classification | Required change |
|---|---|---|
| Requirements metadata | Required | Keep exact pin until upgrade review finishes |
| Discovery adapter | Graceful optional import | Reword: discovery enhancement can degrade, package itself remains required |
| Color conversion | Required direct import | Move behind the adapter boundary |
| UI | Must be independent | Add test forbidding UI imports |
| Native control | Independent | Preserve native UDP implementation |
| Windows package | Expected runtime package | Verify both `site-packages` and embedded `app.zip` |
| License notices | Missing or unverified | Add exact upstream MIT text and third-party notice |

## Recommended dependency boundary

Only `core/pywizlight_adapter.py` may import `pywizlight` after the refactor.

The adapter should expose WizZ-owned immutable values rather than upstream classes:

```python
@dataclass(frozen=True, slots=True)
class PyWizLightCapabilities:
    module_name: str | None
    type_id: str | None
    brightness: bool
    color: bool
    color_temperature: bool
    effects: bool
    kelvin_min: int | None
    kelvin_max: int | None
    white_channels: int | None
    white_to_color_ratio: int | None
    dual_head: bool
    fan: bool
    fan_speed_range: int | None
    supported_scenes: tuple[int, ...]
    source: str
    error: str | None = None
```

Suggested functions:

```python
async def discover_devices(...): ...
async def read_device_capabilities(ip: str, ...): ...
async def read_supported_scenes(ip: str, ...): ...
def display_rgb_to_wiz_channels(...): ...
def wiz_channels_to_display_rgb(...): ...
```

The UI and `ActionSequenceExecutor` must never receive `BulbType`, `wizlight`, `PilotBuilder`, or another upstream class.

## Capability-resolution order

1. Read-only `getModelConfig`.
2. Read-only `getSystemConfig`.
3. `getUserConfig` for old firmware.
4. `pywizlight.get_bulbtype()`.
5. Conservative `moduleName` / `typeId` inference.
6. Manual override keyed by MAC.
7. Safe unknown profile.

Do not infer capabilities only from `getPilot`; the active mode can omit supported color, temperature, scene, ratio, or fan fields.

## Cache rules

Cache normalized capabilities using stable identity:

- primary key: MAC;
- validation inputs: firmware and `moduleName`;
- IP is location, not identity.

Invalidate when firmware, module name, or a user override changes.

## Packaging findings to verify locally

The included read-only audit tool checks:

- pinned and installed versions;
- all imports and textual references;
- package files and approximate installed size;
- upstream license files available in distribution metadata;
- `dist/windows/site-packages`;
- embedded `app.zip`;
- root project license;
- UI-layer imports.

Run:

```powershell
python tools/pywizlight_audit.py --write docs/PYWIZLIGHT_LOCAL_AUDIT.json
```

## Licensing and attribution

`pywizlight` is MIT licensed. No separate permission request is required to use or redistribute it under those terms, but its copyright and license notice must be preserved in distributed copies.

Required future files:

```text
licenses/pywizlight-LICENSE.txt
THIRD_PARTY_NOTICES.md
```

Copy the exact license from the installed/distributed `pywizlight` version; do not reconstruct it from memory.

The Windows ZIP and future installer must include both files.

Recommended acknowledgment:

> WizZ Desktop uses pywizlight, an open-source Python library created by Stephan Traub and maintained by its contributors, for WiZ device discovery, capability detection and color-channel conversion. pywizlight is distributed under the MIT License.

Required independence notice:

> WizZ Desktop is an independent community project and is not affiliated with or endorsed by WiZ Connected or Signify.

## Project-license gate

This audit does not add a license for WizZ Desktop itself.

If no root `LICENSE`, `LICENSE.txt`, `LICENSE.md`, `LICENSE.rst`, or `COPYING` exists, the owner must choose a license before the project is described as open source.

Initial recommendation: **MIT**, because it is short, permissive, compatible with `pywizlight`, and appropriate for a community desktop utility.

## Risks

1. Comments currently call `pywizlight` optional while the color pipeline imports it unconditionally.
2. Capability I/O could accidentally enter the slider hot path during refactoring.
3. `BulbType` could leak into UI code and create long-term coupling.
4. A model-name-only approach could misclassify unknown or new hardware.
5. An upgrade could subtly change color conversion or capability inference.
6. License files may exist in the repository but be omitted from packaged artifacts.
7. Two simultaneous full discovery systems could increase latency and UDP traffic.

## Acceptance criteria for the next implementation phase

- all `pywizlight` imports live in the adapter;
- native UDP remains the hot path;
- adapter calls have timeout and cancellation;
- capability data is normalized and cached by MAC;
- UI imports no upstream package;
- exact upstream license is distributed;
- project license is explicitly selected;
- all current tests remain green;
- physical behavior of the existing bulb is unchanged.
