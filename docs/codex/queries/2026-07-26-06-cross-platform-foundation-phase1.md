# Cross-platform Foundation Phase 1

Status: Completed

Fecha: 2026-07-26

Rama: `feature/v1.3.0-effects-engine-foundation`

ADR relacionado:

- `docs/adr/0004-cross-platform-architecture.md`

## 1. Objetivo

Crear la primera frontera cross-platform de WizZ Desktop sin migrar ninguna
plataforma ni cambiar comportamiento existente.

Phase 1 introduce:

- un modelo inmutable de capacidades efectivas;
- contratos neutrales para integraciones de escritorio;
- fakes determinísticos para tests;
- tests de estados, contratos y fallbacks.

Los targets de producto siguen siendo Windows estable, Linux beta y macOS
experimental, pero esta fase no implementa ni certifica esos niveles.

## 2. Restricciones respetadas

No se modificaron:

- `core/light_controller.py`;
- `core/wiz_protocol.py`;
- `core/action_sequence.py`;
- `config/favorites_manager.py`;
- UI existente;
- Quick Panel;
- packaging, dependencias o workflows.

Tampoco se movió comportamiento Windows, se reemplazaron librerías, se
crearon backends reales ni se añadieron forks por OS.

## 3. Archivos

Código creado:

- `core/platform/__init__.py`;
- `core/platform/capabilities.py`;
- `core/platform/contracts.py`;
- `core/platform/fakes.py`.

Tests creados:

- `tests/test_platform_capabilities.py`.

Documentación creada o actualizada:

- `docs/codex/PROJECT_CONTEXT.md`;
- `docs/codex/queries/2026-07-26-06-cross-platform-foundation-phase1.md`;
- `docs/codex/plans/2026-07-26-cross-platform-foundation-phase1.md`.

## 4. Modelo de capacidades

`CapabilityStatus` define exactamente cuatro estados:

- `available`;
- `unavailable`;
- `degraded`;
- `permission_required`.

`CapabilityState` es un dataclass inmutable con:

- `status`;
- `reason` opcional y normalizado;
- `is_available`;
- `is_usable`.

`available` y `degraded` son utilizables. `unavailable` y
`permission_required` no lo son. La distinción permite simular una integración
que funciona con limitaciones sin presentarla como soporte pleno.

`DesktopCapabilities` es un snapshot inmutable con estados independientes
para:

- registro y grabación de hotkeys;
- tray y default action;
- start at login;
- show, hide, restore y focus de ventana;
- work area positioning;
- frameless, always-on-top y taskbar skip;
- exclusión y activación de instancia única;
- apertura de carpetas.

Todos los campos usan `CapabilityState` y parten en `unavailable`. El modelo
no detecta el OS ni contiene una tabla por plataforma.

## 5. Contratos

`core/platform/contracts.py` define `Protocol` verificables en runtime:

- `HotkeyService`: register, unregister, record y capabilities;
- `TrayBackend`: start, update menu, stop, running y capabilities;
- `AutostartService`: estado enabled, cambio de start-at-login y
  capabilities;
- `WindowService`: show, hide, restore, focus, work area y capabilities;
- `SingleInstanceService`: acquire/release separados de activate-existing;
- `SystemIntegrationService`: open-folder y capabilities.

Son contratos estructurales. No heredan de clases Windows, Flet, `keyboard`,
`pystray` ni servicios actuales.

El snapshot completo se expone en cada contrato para que futuros consumidores
puedan decidir por operación sin inferir capacidades a partir del nombre del
OS.

## 6. Fakes

`core/platform/fakes.py` incluye:

- `FakeHotkeyService`;
- `FakeTrayBackend`;
- `FakeAutostartService`;
- `FakeWindowService`;
- `FakeSingleInstanceService`;
- `FakeSystemIntegrationService`.

Los fakes:

- reciben un `DesktopCapabilities` inmutable;
- guardan sólo estado in-memory;
- permiten simular available, unavailable, degraded y
  permission-required;
- ejecutan operaciones cuando la capacidad es available o degraded;
- rechazan sin side effects cuando es unavailable o permission-required;
- no importan ni llaman backends nativos.

`FakeSingleInstanceService` mantiene exclusión y activación como resultados
independientes. `FakeWindowService` evalúa show, hide, restore, focus y work
area por separado. Esto permite probar degradaciones parciales reales en
fases posteriores.

## 7. TDD

Primer ciclo:

1. se escribieron los tests de modelos;
2. pytest falló con `ModuleNotFoundError: core.platform`;
3. se implementaron los modelos mínimos;
4. resultado focalizado: `10 passed`.

Segundo ciclo:

1. se agregaron tests de contratos y fakes;
2. pytest falló con `ModuleNotFoundError: core.platform.contracts`;
3. se implementaron Protocols y fakes mínimos;
4. resultado focalizado: `20 passed`.

La auto-revisión eliminó una propiedad de conveniencia no requerida para
mantener la API mínima.

## 8. Validación

Se usó `.venv\Scripts\python.exe` porque `python` no está disponible en el
`PATH` de esta sesión.

Resultados:

- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`:
  correcto;
- `python -m pytest -q`: `279 passed`, `98 warnings`;
- `python tools/i18n_audit.py`: 579 claves ES/EN y cero strings sospechosos;
- `git diff --check`: correcto.

Las 98 advertencias son deprecaciones Flet emitidas por tests de la UI
preexistente. Phase 1 no modificó esos componentes.

## 9. Limitaciones deliberadas

Esta foundation todavía no:

- selecciona plataforma o adapter;
- detecta capacidades reales;
- envuelve `RegisterHotKey`, `keyboard`, `pystray`, Registry, Win32 o file
  locks;
- conecta contracts a `main.py`, settings, tray o Quick Panel;
- cambia copy o fallbacks de UI;
- produce builds Linux/macOS;
- valida X11, Wayland, macOS o hardware.

Los fakes demuestran los contratos, no soporte nativo.

## 10. Próximos pasos

En fases separadas y después de aprobar Phase 1:

1. congelar mediante contract tests el comportamiento Windows existente;
2. crear una composición de plataforma sin conectar todavía UI completa;
3. encapsular un servicio Windows por vez detrás de los contratos;
4. agregar fallbacks UI capability-driven;
5. diseñar IPC Unix para activación de instancia;
6. evaluar backends Linux y macOS sin asumir una librería;
7. producir builds nativos y ejecutar la matriz del ADR 0004.

No se debe iniciar una migración Linux/macOS ni volver a Effects Engine hasta
revisar el alcance siguiente.

## 11. Estado Git

No se hizo commit, merge ni push. El worktree conserva cambios documentales
preexistentes además de esta fase y queda esperando revisión.
