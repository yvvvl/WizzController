# Comment and docstring style

Technical comments and docstrings are written in English. User-visible text belongs in the localization catalogs.

## Rule

Comments explain **why**, a protocol constraint, a race, or an invariant. The code explains **what**.

### Avoid

```python
# Set brightness.
params["dimming"] = value
```

### Prefer

```python
# WiZ brightness is independent of RGB and uses a 1–100 scale.
params["dimming"] = value
```

## Keep comments when they protect

- UDP retry or fire-and-forget behavior;
- thread and event-loop boundaries;
- firmware compatibility;
- capability fallbacks;
- MAC-based identity;
- cache invalidation;
- packaging/runtime constraints;
- non-obvious physical color conversion;
- an intentionally conservative unsupported-device path.

## Remove

- phase-history labels;
- comments that repeat a function name;
- large implementation essays;
- stale statements such as “optional” when the import is required;
- commented-out code;
- obvious step-by-step narration.

Long explanations belong in `docs/` or an ADR.

Public APIs use concise docstrings. Trivial private helpers do not require docstrings unless they enforce a non-obvious invariant.

Third-party-derived code must include a short source and license note in the file, while the full notice lives in `THIRD_PARTY_NOTICES.md`.
