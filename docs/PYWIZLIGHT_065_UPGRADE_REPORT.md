# pywizlight 0.6.5 upgrade report

**Current pin:** `0.6.3`  
**Latest researched release:** `0.6.5`  
**Decision:** **Postpone the upgrade until the adapter boundary and capability fixtures exist.**

## Public metadata comparison

| Property | 0.6.3 | 0.6.5 |
|---|---:|---:|
| Release date | 2025-06-10 | 2026-07-08 |
| Python requirement | `>=3.7` | `>=3.11` |
| Wheel size | 59.0 kB | 62.1 kB |
| Source size | 43.8 kB | 47.0 kB |
| License | MIT | MIT |

WizZ Desktop supports Python `>=3.11,<3.14`, so the declared Python requirement is compatible.

## Why the upgrade is not automatic

The public package description confirms that core concepts still exist, but that is not enough to certify:

- identical `BulbType` fields;
- identical discovery behavior;
- identical RGB/CW output;
- identical firmware fallback;
- identical supported-scene classification;
- identical timeout and retry behavior.

WizZ Desktop currently imports upstream color functions directly, so even a small behavior change could alter physical color reproduction.

## Required evidence before upgrade

- source diff for `rgbcw.py`, `bulblibrary.py`, `bulb.py`, discovery and scenes;
- adapter contract tests against both versions;
- fixture tests for RGB/TW/DW/socket/unknown devices;
- physical probe with the currently available bulb;
- clean Windows build and runtime verification;
- exact 0.6.5 license bundled in output.

## Upgrade commit

Only after the evidence is green:

```text
chore: upgrade pywizlight to 0.6.5
```

The version change must not be mixed with capability refactors.
