# ADR 0003: Effects Engine logical-to-physical architecture

- Status: Accepted
- Date: 2026-07-26
- Scope: Effects Engine, RGBIC, Screen Sync and calibration

## Context

The first RGBIC foundation treated a zone weight/width as a relative
proportion. New technical information from TechAntohere corrects that
assumption: WiZ RGBIC `width` is an absolute span of physical segments.

Steps are applied sequentially from the start of the strip. A step with
`width: 1` occupies one physical segment and `width: 2` occupies two. Twelve
steps therefore describe twelve entries, not necessarily twelve physical
segments and not necessarily the full installed strip.

The firmware does not necessarily know the installed length. A strip may be
cut while continuing to report the same model. Product density, installed
length and user calibration all affect the number of usable physical
segments. A device model is therefore insufficient to derive physical
coverage.

The observed limit of 12 RGBIC entries belongs to the physical WiZ payload
shape, not to the logical effect description. Logical sources may therefore
produce more than 12 regions or colors. When they do, a deterministic
compression step must reduce that logical sequence before physical mapping and
encoding.

Reverse-engineering observations also show a global `elm.modifier` field:

- `modifier: 100` corresponds to static color in the observed behavior;
- values from 101 through 125 appear to select internal effects used by the
  WiZ app;
- other ranges also exhibit effect behavior;
- the exact value map is incomplete and is not an official protocol contract.

The scene container is also not a stable constant. `sceneId: 257` worked in
an initial observation, but after a firmware update that slot appeared to be
overwritten by an effect stored on the device. Using `sceneId: 258` restored
the expected behavior. This indicates that candidate slots may depend on
firmware and internal device state.

A successful WiZ transport operation only confirms that a command was sent or
acknowledged according to the transport contract. It does not prove that the
requested RGBIC effect was applied as intended.

## Decision

The architecture separates effect intent, physical mapping and output:

```text
Effect Source (Screen Sync, Gradient, Music)
        |
Logical Effect Frame
        |
Physical Mapper  <---------------- Calibration Profile
        |
RGBIC Steps (color + width + brightness)
        |
RGBIC Program (steps + global modifier + support)
        |
LightController
        |
WizProtocol
```

### Logical Effect Zones

Logical zones represent effect intent such as left, center, right, background
or accent. They may carry colors and logical ordering, but they do not know
LED counts, WiZ segments, strip density, installed length or protocol fields.

The Effects Engine and all effect sources operate exclusively on this logical
representation. They remain independent of physical hardware and transport.

Logical frames are not capped by the observed WiZ payload ceiling. That limit
applies only to the physical RGBIC program.

### Physical Mapper

`PhysicalMapper` converts a logical frame into physical RGBIC steps. It uses a
calibration profile associated with the concrete installation, not a global
product-model table.

The mapper owns decisions about how logical regions cover the calibrated
physical span. It does not serialize WiZ payloads and does not send network
traffic.

### Physical RGBIC Steps

An `RGBICStep` conceptually contains:

- a color;
- an absolute positive `width` measured in physical segments;
- an optional step brightness value;
- a position implied by sequential order.

Steps are a physical output representation. They must not be used as the
logical effect model.

The observed `modifier` belongs to the enclosing `elm` program, not to each
step. It remains a raw integer. No enum, named effect catalog or exhaustive
range validation is approved. The observed value 100 may be documented as
static color, while 101-125 and other ranges remain engineering observations
that require fixtures and hardware evidence.

### Calibration

RGBIC requires calibration because the installed strip may have a different
length or density than another device with the same model identifier.
Calibration must be capable of representing the usable physical segment span
for a specific installation, including cut strips.

The calibration flow and persistence format are intentionally deferred. This
ADR only fixes ownership and architectural boundaries.

### Output ownership

`LightController` remains the single owner of device output and realtime
ownership. A pure RGBIC encoder and an experimental single-send bridge already
exist behind that boundary. They can serialize already-mapped physical steps
to a chosen scene container and `elm.steps`, but they must not make logical
mapping decisions. Slot selection still requires capabilities, probing,
fallback candidates and validation of applied behavior; it must not hardcode
257 or infer a slot only from a firmware version.

`WizProtocol` remains the generic WiZ transport. Effects, Screen Sync,
calibration and `PhysicalMapper` must not open sockets or import the protocol
layer.

## Future RGBIC physical mapping

The future contract has six explicit boundaries:

1. **Logical vs physical:** a `LogicalEffectFrame` carries regions and colors
   only. It cannot contain `width`, `modifier`, WiZ fields, LEDs or segments.
2. **Calibration:** a profile for one concrete installation provides the
   usable physical span. It is not inferred from the device model.
3. **Physical mapping:** `PhysicalMapper` combines logical intent, calibration
   and a future physical-output policy to produce ordered `RGBICStep` values
   containing `color`, absolute `width` and optional brightness.
4. **Logical compression:** if a logical source yields more than 12 color
   regions, a deterministic compression step reduces that sequence to a
   physical-safe count while preserving order and approximate visual intent.
5. **Program assembly and encoder:** a program layer adds global
   `modifier`/`support`, and an encoder serializes that structure through a
   validated scene container and `elm.steps`. It does not choose widths,
   interpret logical regions or define modifier meanings.
6. **Applied-state validation:** the output layer distinguishes transport
   success from evidence that the requested effect was actually applied. A
   failed candidate may trigger a bounded fallback or a reported unsupported
   state, never an unbounded retry loop.

The encoder remains behind `LightController`. Until modifier ranges are
documented and tested, it must treat the value as experimental data rather
than a stable public enum. Until scene container behavior is characterized,
candidate slots remain probed runtime data rather than protocol constants.

## Explicitly rejected

- A fixed lookup table from device model to physical segment count.
- Assuming that a product model determines installed strip length.
- Treating the observed limit of 12 steps as a physical segment count.
- Treating the observed limit of 12 steps as a logical-frame color limit.
- Treating `width` as a relative proportion.
- Mixing logical effect zones with physical RGBIC steps.
- Adding a `modifier` enum or named internal-effect catalog now.
- Hardcoding `sceneId: 257`, `sceneId: 258` or another slot.
- A fixed lookup table from firmware version to `sceneId`.
- Selecting a slot using firmware version alone.
- Treating transport success as proof that an RGBIC effect was applied.
- Putting `width` or `modifier` in `LogicalEffectFrame`.
- Letting the encoder infer calibration or modifier semantics.
- Letting Screen Sync or another effect source choose protocol widths.
- Letting an RGBIC encoder own calibration or effect semantics.
- Creating a second output controller beside `LightController`.

## Impact on the current foundation

The obsolete `RGBICZone.weight` assumption has already been replaced in the
Python foundation. The current internal model now includes:

- `RGBICFrame` as logical, compressible intent;
- deterministic logical compression before physical mapping when needed;
- `CalibrationProfile` for installation-specific physical span;
- `RGBICStep` as physical sequential output;
- `RGBICProgram` as the physical container with global `modifier`/`support`;
- a pure encoder to WiZ params;
- an experimental bridge behind `LightController`.

Those pieces validate the architectural separation defined here. They do not
yet constitute production RGBIC support: scheduler, streaming, realtime
ownership policies, stable slot selection, capability wiring and end-user UX
remain future work.

This ADR therefore permits the current experimental bridge and pure encoder,
while still rejecting alternative sockets, hardcoded slots and transport-led
effect semantics.

## Consequences

Positive:

- effect sources remain portable and hardware-independent;
- cut strips and installation differences can be represented;
- mapping can be simulated and tested without UDP or hardware;
- encoding and transport remain isolated behind the existing output owner.

Costs:

- RGBIC setup needs a calibration flow and persisted profile;
- a logical frame cannot be encoded without calibration or an explicit safe
  fallback;
- modifier values require captured fixtures and hardware/community validation
  before stable semantics can be assigned;
- scene containers require capability-aware probing, bounded fallback and
  applied-behavior validation;
- scheduler, streaming and stable runtime policies require separate future
  phases.

## Validation strategy

Validate logical frames, calibration fixtures, mapping, raw modifier
pass-through, candidate-slot policies and encoder payloads through pure
simulators and contract tests. Transport success and effect-applied outcomes
must be represented separately in those tests.

Initial hardware evidence and sanitized fixtures already exist from community
testing. Further end-to-end validation should continue through the beta
validator flow, using explicit user-provided calibration and manual visual
confirmation without claiming production support.