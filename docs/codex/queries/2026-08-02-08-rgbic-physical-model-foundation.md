# RGBIC Physical Model Foundation

Status: Completed

Fecha: 2026-08-02

Rama: `feature/v1.3.0-effects-engine-foundation`

Relacionado:

- `docs/adr/0003-effects-engine-architecture.md`
- `docs/codex/PROJECT_CONTEXT.md`
- `docs/codex/queries/2026-07-26-07-rgbic-hardware-validation.md`

## 1. Objetivo

Actualizar la foundation interna RGBIC para que el modelo Python refleje la
separación ya aprobada entre:

- intención lógica del efecto;
- calibración física por instalación;
- steps RGBIC físicos secuenciales.

La fase no implementa comunicación WiZ, encoder, scheduler, realtime session
ni cambios en `LightController` o `WizProtocol`.

## 2. Transición desde `RGBICZone.weight`

La foundation anterior modelaba RGBIC con `RGBICZone.weight` bajo la semántica
ya descartada de un ancho/peso relativo. Esa representación se reemplaza por:

- `RGBICFrame` como frame lógico de colores;
- `CalibrationProfile` como descripción mínima de la instalación física;
- `RGBICStep` como salida física con `color`, `width`, `modifier` y
  `brightness` opcional.

El `width` físico absoluto ya no vive en el frame lógico.

## 3. Modelo implementado

### `RGBICFrame`

- conserva el límite confirmado de 12 entradas;
- contiene únicamente colores lógicos;
- no conoce `width`, `modifier`, WiZ, `sceneId`, `elm` ni transporte.

### `CalibrationProfile`

- contiene `physical_segments`;
- representa una instalación concreta;
- no contiene modelo WiZ, firmware, `sceneId` ni metadata de transporte.

### `RGBICStep`

- representa salida física secuencial;
- valida `width > 0`;
- mantiene `modifier` como entero experimental;
- permite `brightness` opcional.

## 4. Mapper puro

Se añadió `core/effects/rgbic_mapper.py` con `map_rgbic_frame()`.

Responsabilidades:

- convertir un frame lógico y una calibración en `RGBICStep[]`;
- respetar el máximo de 12 steps desde el frame lógico;
- cubrir exactamente `physical_segments` cuando el frame contiene colores;
- distribuir widths con la fórmula aprobada:

```text
width[i] = floor((i+1)*N/K) - floor(i*N/K)
```

donde `N` es la cantidad de segmentos físicos y `K` la cantidad de colores
lógicos.

La implementación actual usa una política uniforme. No introduce heurísticas
de hardware, probing ni encoding.

## 5. Simulador

`core/effects/rgbic_simulator.py` ahora expande steps físicos a segmentos
secuenciales reales.

Representa:

- número de segmento físico;
- step secuencial de origen;
- color;
- `modifier`;
- `brightness`;
- padding negro cuando una simulación manual no cubre toda la calibración.

No representa `sceneId`, `elm`, UDP ni respuestas WiZ.

## 6. Archivos

Creado o actualizado en esta fase:

- `core/effects/models.py`
- `core/effects/rgbic_mapper.py`
- `core/effects/rgbic_simulator.py`
- `core/effects/__init__.py`
- `tests/test_effect_models.py`
- `tests/test_rgbic_mapper.py`
- `tests/test_rgbic_simulator.py`
- `docs/codex/PROJECT_CONTEXT.md`
- `docs/codex/queries/2026-08-02-08-rgbic-physical-model-foundation.md`

Sin cambios:

- `core/light_controller.py`
- `core/wiz_protocol.py`
- encoder RGBIC, scheduler, realtime session y UI

## 7. Decisiones

- mantener `RGBICFrame` como intención lógica y `RGBICStep` como salida física;
- no reintroducir `weight` relativo;
- no crear tabla `modelo -> segmentos`;
- no fijar `sceneId`;
- no convertir `modifier` en enum;
- no conectar esta foundation a hardware ni transporte;
- validar primero con simuladores y tests.

## 8. Validación

Red/Green focalizado:

- tests rojos iniciales: fallaron por ausencia de `CalibrationProfile`,
  `RGBICStep` y mapper físico;
- tests verdes focalizados:
  `.venv\Scripts\pytest.exe -q tests/test_effect_models.py tests/test_rgbic_mapper.py tests/test_rgbic_simulator.py`
  -> `47 passed`.

Validación completa de la fase:

- `.venv\Scripts\pytest.exe -q` -> `294 passed`, `3 failed`, `98 warnings`.
  Los tres fallos pertenecen a `tests/test_pywizlight_audit_contract.py` y
  refieren a archivos documentales preexistentes hoy ausentes:
  `docs/PYWIZLIGHT_INTEGRATION_AUDIT.md` y
  `docs/PYWIZLIGHT_065_UPGRADE_REPORT.md`.
- `.venv\Scripts\python.exe -m compileall -q main.py app_meta.py core config ui localization tests tools`
  -> exit code 0.
- `.venv\Scripts\python.exe tools/i18n_audit.py`
  -> `Catalogs OK: 579 keys · en/es`, `Potential hardcoded UI strings: 0`.
- `git diff --check` -> exit code 0.
- `git status` revisado.
- `git diff --stat` revisado.

## 9. Próximos pasos

- diseñar persistencia y flujo de calibración por instalación;
- ampliar el mapper con políticas físicas adicionales cuando existan fuentes
  de efecto que las necesiten;
- diseñar el encoder de `RGBICStep` a un slot validado y `elm.steps`;
- validar luego con hardware comunitario sin modificar todavía el transporte
  productivo.
