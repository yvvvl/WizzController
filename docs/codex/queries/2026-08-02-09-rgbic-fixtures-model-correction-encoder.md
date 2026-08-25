# RGBIC fixtures, model correction and pure encoder foundation

Status: Completed

Fecha: 2026-08-02

Rama: `feature/v1.3.0-effects-engine-foundation`

Relacionado:

- `docs/codex/queries/2026-07-26-07-rgbic-hardware-validation.md`
- `docs/codex/queries/2026-08-02-08-rgbic-physical-model-foundation.md`
- `docs/codex/PROJECT_CONTEXT.md`

## 1. Objetivo

Incorporar la evidencia física real disponible, corregir la ubicación de
`modifier` en el modelo RGBIC y añadir un encoder puro hacia params de
`setPilot`, sin tocar todavía transporte, scheduler, UI ni realtime session.

## 2. Corrección del modelo

La evidence real corrigió una suposición del worktree:

- `RGBICStep` ya no contiene `modifier`;
- `RGBICStep` conserva únicamente `color`, `width` y `brightness` opcional;
- `RGBICProgram` pasa a representar la salida física completa con:
  - `steps`
  - `modifier` global
  - `support`

Esto refleja la observación real de `elm`:

- `elm.modifier` es global;
- `elm.support` también es global y sigue siendo experimental;
- `width` y `brightness` viven en cada step codificado.

## 3. Encoder puro

Se añadió `core/effects/rgbic_encoder.py`.

El encoder:

- recibe `RGBICProgram` y `scene_id`;
- produce un `dict` de params para `WizProtocol.send_pilot()`;
- no abre sockets;
- no importa `WizProtocol`;
- no importa `LightController`;
- no decide slots;
- no interpreta `success: true` como validación visual;
- no incluye MAC.

Cada step se serializa como un array de 13 enteros:

- índice 0: `0`
- índices 1/2/3: `RGB`
- índices 4/5/6: `0`
- índice 7: `brightness`
- índices 8/9/10/11: `0`
- índice 12: `width`

Si `brightness` no está presente en el step, el encoder usa `100`.

## 4. Fixtures reales

Se añadieron fixtures sanitizados en `tests/fixtures/rgbic/` para registrar:

- dispositivo real `ESP25_MHORGB_01` firmware `1.38.0`;
- instalación calibrada de 17 segmentos;
- diferencia entre `sceneId: 257` ocupado y `sceneId: 258` vacío;
- límite confirmado de 12 steps;
- cobertura parcial y total para 17 segmentos.

No se incluyeron IP, MAC real, `homeId`, `roomId`, nombres de red ni
identificadores personales.

## 5. Tests actualizados

Se actualizaron o añadieron tests para:

- `RGBICStep` sin `modifier`;
- `RGBICProgram` con `modifier` global y `support`;
- preservación de `support`;
- límite de 12 steps;
- encoding exacto a arrays de 13 elementos;
- `RGB` en índices 1/2/3;
- `brightness` en índice 7;
- `width` en índice 12;
- ceros en índices desconocidos;
- preservación de `sceneId`;
- omisión de MAC;
- fixtures reales;
- distribución uniforme para 17 segmentos;
- simulador sin `modifier` por step;
- rutas documentales canónicas de `pywizlight`.

## 6. Archivos

Creados:

- `core/effects/rgbic_encoder.py`
- `tests/test_rgbic_encoder.py`
- `tests/fixtures/rgbic/device-esp25-mhorgb-01-fw-1.38.0.json`
- `tests/fixtures/rgbic/scene-257-occupied-success-visually-wrong.json`
- `tests/fixtures/rgbic/scene-258-empty-success-visually-correct.json`
- `tests/fixtures/rgbic/step-limit-fw-1.38.0.json`
- `tests/fixtures/rgbic/width-coverage-17-segments.json`
- `docs/codex/queries/2026-08-02-09-rgbic-fixtures-model-correction-encoder.md`

Modificados:

- `core/effects/models.py`
- `core/effects/rgbic_mapper.py`
- `core/effects/rgbic_simulator.py`
- `core/effects/__init__.py`
- `tests/test_effect_models.py`
- `tests/test_rgbic_mapper.py`
- `tests/test_rgbic_simulator.py`
- `tests/test_pywizlight_audit_contract.py`
- `docs/codex/queries/2026-07-26-07-rgbic-hardware-validation.md`
- `docs/codex/PROJECT_CONTEXT.md`

## 7. Riesgos pendientes

- `support` sigue siendo experimental;
- `sceneId: 258` no debe asumirse como universal;
- `sceneId: 256` sigue sin probarse;
- `success: true` sigue sin equivaler a aplicación visual confirmada;
- el encoder puro aún no está conectado al transporte productivo.
