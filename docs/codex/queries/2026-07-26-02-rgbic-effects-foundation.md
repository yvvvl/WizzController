# Dynamic Effects / RGBIC Foundation

Fecha: 2026-07-26

Rama: `feature/v1.3.0-effects-engine-foundation`

Estado: implementación completada, pendiente de revisión

## 1. Estado inicial

- La suite base contiene 227 tests y pasa completa.
- `LightController` ya delega los comandos en `WizProtocol.send_pilot`.
- `WizProtocol.send_pilot` recibe un diccionario genérico de parámetros y lo
  serializa sin filtrar claves; esto permite caracterizar `elm` mediante tests
  sin introducir una rama especial para RGBIC.
- El discovery y el modelo actual de capacidades no conocen RGBIC.
- No existía una capa `core/effects`.

## 2. Información técnica aportada

TechAntohere compartió observaciones obtenidas al investigar tiras RGBIC WiZ y
el proyecto WizScreenSyncController:

- RGBIC utiliza `setPilot`.
- `sceneId: 257` actúa como contenedor.
- Los datos de zonas se transportan en `elm.steps`.
- Se observaron hasta 12 zonas.
- El peso/ancho de un step describe una proporción de zona, no una cantidad de
  LEDs.

Esta implementación usa únicamente esos conceptos. No copia código de
WizScreenSyncController. La atribución para distribución permanece pendiente
de confirmar permiso y licencia.

## 3. Decisiones técnicas

- Los valores de color, zonas, frames y capacidades serán modelos inmutables.
- Las colecciones se normalizarán a tuplas para preservar la inmutabilidad
  profunda del frame.
- Los colores RGB se validarán en el intervalo 0–255.
- El límite inicial será de 12 zonas y un frame RGBIC vacío será válido.
- El peso/ancho será un número positivo y finito opcional, sin interpretarlo
  como cantidad de LEDs.
- El simulador será una función pura que siempre producirá 12 posiciones
  verificables y completará las faltantes con negro.
- Las capacidades futuras vivirán en un modelo separado; no se modificará el
  discovery real.
- El protocolo conservará su transporte genérico actual. Se añadirán tests de
  contrato para payloads normales, `elm` anidado y claves desconocidas.

## 4. Arquitectura objetivo

```text
Effect Engine (futuro)
        |
EffectFrame / RGBICFrame
        |
LightController
        |
WizProtocol
```

La capa `core/effects` no importará UDP, sockets, `WizProtocol`, Flet ni
PySide.

## 5. Plan de implementación

1. [x] Crear tests rojos para modelos, validaciones y capacidades.
2. [x] Implementar los modelos mínimos en `core/effects/models.py`.
3. [x] Crear tests rojos para la representación simulada.
4. [x] Implementar `core/effects/rgbic_simulator.py`.
5. [x] Caracterizar mediante tests el transporte genérico de `send_pilot`.
6. [x] Añadir el borrador interno de atribución.
7. [x] Ejecutar compilación, suite completa, auditoría i18n y validaciones Git.

## 6. Archivos modificados

- `core/effects/__init__.py`
  - Expone la API pública inicial de efectos.
- `core/effects/models.py`
  - Añade `RGBColor`, `EffectFrame`, `RGBICZone`, `RGBICFrame` y
    `DeviceCapabilities`.
- `core/effects/rgbic_simulator.py`
  - Añade la representación pura de 12 zonas con padding negro.
- `tests/test_effect_models.py`
  - Verifica creación, inmutabilidad, validaciones, límites, frame vacío,
    pesos y capacidades.
- `tests/test_rgbic_simulator.py`
  - Verifica 12 zonas, padding, frame vacío y conservación de pesos.
- `tests/test_wiz_protocol_extended_params.py`
  - Caracteriza el transporte de payload normal, `elm` y claves desconocidas.
- `THIRD_PARTY_NOTICES.md`
  - Añade únicamente un borrador interno, no distribuible, pendiente de
    permiso/licencia.
- `docs/codex/queries/2026-07-26-02-rgbic-effects-foundation.md`
  - Registra el análisis, decisiones y evidencia de esta fase.

`core/wiz_protocol.py`, `core/wiz_capabilities.py`, discovery,
`LightController` y la UI no fueron modificados.

## 7. Tests

- Baseline: `227 passed`.
- Tests focalizados de esta fase: `32 passed`.
- `python -m compileall -q main.py app_meta.py core config ui localization tests tools`:
  exit code 0.
- `python -m pytest -q`: `259 passed`, con 98 advertencias deprecadas ya
  existentes en componentes Flet.
- `python tools/i18n_audit.py`: 579 claves en/es y 0 strings UI sospechosos.
- `git diff --check`: sin errores.

## 8. Próximos pasos

- Definir el Effect Engine y su scheduler en una fase posterior.
- Diseñar el adaptador explícito entre `RGBICFrame` y los parámetros WiZ
  `sceneId`/`elm`.
- Confirmar permiso/licencia antes de publicar atribuciones definitivas.
- Validar el comportamiento contra hardware RGBIC real sin acoplarlo a los
  modelos de efectos.
