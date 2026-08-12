# Cross-platform Foundation Phase 1 Implementation Plan

Status: Completed

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immutable desktop capability models, platform-neutral service
contracts and deterministic fakes without migrating any existing backend.

**Architecture:** `core.platform.capabilities` owns a platform-independent
snapshot of effective desktop support. `core.platform.contracts` defines
runtime-checkable `Protocol` boundaries, and `core.platform.fakes` implements
those boundaries using only the capability snapshot and in-memory state.

**Tech Stack:** Python 3.11+, frozen/slots dataclasses, `Enum`,
`typing.Protocol`, pytest.

## Global Constraints

- Do not modify `core/light_controller.py`, `core/wiz_protocol.py`,
  `core/action_sequence.py` or `config/favorites_manager.py`.
- Do not modify existing UI, Quick Panel or packaging.
- Do not move existing Windows behavior or replace dependencies.
- Do not add OS detection, real adapters or per-OS forks.
- Do not commit, merge or push.
- Follow strict red-green-refactor TDD.

---

### Task 1: Immutable capability model

**Files:**

- Create: `tests/test_platform_capabilities.py`
- Create: `core/platform/__init__.py`
- Create: `core/platform/capabilities.py`

**Interfaces:**

- Produces: `CapabilityStatus`, `CapabilityState` and
  `DesktopCapabilities`.
- `CapabilityState.is_usable` is true only for `available` and `degraded`.
- Every `DesktopCapabilities` field contains a `CapabilityState` and defaults
  to `unavailable`.

- [ ] **Step 1: Write failing model tests**

Test literal values for all four statuses, optional normalized reasons,
immutability, default unavailable fields and explicit mixed capability
snapshots.

- [ ] **Step 2: Verify the tests fail for the missing package**

Run:

```powershell
python -m pytest -q tests/test_platform_capabilities.py
```

Expected: collection fails because `core.platform` does not exist.

- [ ] **Step 3: Implement the minimum immutable models**

Create a string enum with `available`, `unavailable`, `degraded` and
`permission_required`; a frozen `CapabilityState`; and a frozen
`DesktopCapabilities` with one field per ADR 0004 capability.

- [ ] **Step 4: Verify the model tests pass**

Run:

```powershell
python -m pytest -q tests/test_platform_capabilities.py
```

Expected: all model tests pass.

### Task 2: Service contracts and deterministic fakes

**Files:**

- Modify: `tests/test_platform_capabilities.py`
- Create: `core/platform/contracts.py`
- Create: `core/platform/fakes.py`
- Modify: `core/platform/__init__.py`

**Interfaces:**

- Produces: runtime-checkable `HotkeyService`, `TrayBackend`,
  `AutostartService`, `WindowService`, `SingleInstanceService` and
  `SystemIntegrationService`.
- Produces: `FakeHotkeyService`, `FakeTrayBackend`,
  `FakeAutostartService`, `FakeWindowService`,
  `FakeSingleInstanceService` and `FakeSystemIntegrationService`.
- All services expose the immutable `DesktopCapabilities` snapshot.
- Fake operations succeed for `available` and `degraded`; they fail without
  side effects for `unavailable` and `permission_required`.

- [ ] **Step 1: Add failing contract and fake tests**

Test runtime protocol conformance, fake hotkey registration/triggering, tray
lifecycle/menu state, autostart state, window operation history/work area,
separate single-instance exclusion/activation and open-folder history.

- [ ] **Step 2: Verify failure is caused by missing contracts/fakes**

Run:

```powershell
python -m pytest -q tests/test_platform_capabilities.py
```

Expected: collection fails importing `core.platform.contracts` or
`core.platform.fakes`.

- [ ] **Step 3: Implement protocols and minimum in-memory fakes**

Use no OS imports and no existing Windows services. Keep callback, menu, path
and work-area types generic and deterministic.

- [ ] **Step 4: Verify focused tests pass**

Run:

```powershell
python -m pytest -q tests/test_platform_capabilities.py
```

Expected: all platform foundation tests pass.

### Task 3: Project documentation and full verification

**Files:**

- Create:
  `docs/codex/queries/2026-07-26-06-cross-platform-foundation-phase1.md`
- Modify: `docs/codex/PROJECT_CONTEXT.md`

**Interfaces:**

- Documents the approved ADR, created boundaries, deliberate limitations,
  validation evidence and next implementation phase.

- [ ] **Step 1: Write the phase report and focused context update**

Record that no real backend, UI wiring, OS migration or packaging change was
made.

- [ ] **Step 2: Run required validation**

```powershell
python -m compileall -q main.py app_meta.py core config ui localization tests tools
python -m pytest -q
python tools/i18n_audit.py
git diff --check
git status --short
git diff --stat
```

- [ ] **Step 3: Review scope**

Confirm that changed production paths are limited to `core/platform/`, that
all prohibited files remain untouched by this phase, and that no commit,
merge or push occurred.
