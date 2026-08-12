# Dynamic Effects / RGBIC Foundation

Status: Completed

Fecha: 2026-07-26

Rama: `feature/v1.3.0-effects-engine-foundation`

> **Corrección posterior:** este reporte registró `width`/`weight` como una
> proporción relativa. Esa interpretación es incorrecta. La corrección
> arquitectónica se documenta en
> `2026-07-26-03-rgbic-width-model-correction.md`: `width` es un span físico
> absoluto de segmentos y no debe mezclarse con zonas lógicas.
>
> `sceneId: 257` también era sólo una observación inicial. Después de una
> actualización de firmware pareció quedar ocupado por un efecto guardado y
> 258 recuperó el comportamiento. Ningún slot es una constante y un envío
> exitoso no demuestra que el efecto haya sido aplicado.

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
- `sceneId: 257` actuó como contenedor en la observación inicial; evidencia
  posterior demostró que el slot puede variar con firmware/estado interno.
- Los datos de zonas se transportan en `elm.steps`.
- Se observaron hasta 12 entradas, llamadas “zonas” durante esta fase y
  corregidas posteriormente como steps físicos.
- En esta fase se asumió que el peso/ancho describía una proporción de zona.
  Información posterior de TechAntohere corrigió ese supuesto: `width`
  describe cuántos segmentos físicos consecutivos ocupa el step.

Esta implementación usa únicamente esos conceptos. No copia código de
WizScreenSyncController. La atribución para distribución permanece pendiente
de confirmar permiso y licencia.

## 3. Decisiones técnicas

- Los valores de color, zonas, frames y capacidades serán modelos inmutables.
- Las colecciones se normalizarán a tuplas para preservar la inmutabilidad
  profunda del frame.
- Los colores RGB se validarán en el intervalo 0–255.
- El modelo provisional limitará a 12 entradas llamadas zonas y un frame
  RGBIC vacío será válido. Ese límite no representa longitud física.
- El campo `weight` se modeló como un número positivo y finito bajo el
  supuesto anterior. No debe interpretarse como una proporción ni usarse como
  contrato físico definitivo; el modelo requiere separación conceptual antes
  de cualquier integración productiva.
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

La arquitectura corregida añade límites que esta foundation todavía no
implementa:

```text
Effect Source
      |
Logical Effect Frame
      |
Physical Mapper  <--- Calibration Profile
      |
RGBIC Steps (width físico absoluto)
      |
LightController
      |
WizProtocol
```

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
  - Añade la representación pura de 12 entradas provisionales con padding
    negro, sin validar cobertura física.
- `tests/test_effect_models.py`
  - Verifica creación, inmutabilidad, validaciones, límites, frame vacío,
    pesos y capacidades.
- `tests/test_rgbic_simulator.py`
  - Verifica 12 entradas, padding, frame vacío y conservación de pesos bajo el
    contrato provisional.
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
- Corregir en una fase futura la separación entre zonas lógicas y steps
  físicos; el modelo actual no debe usarse como payload de hardware.
- Diseñar el flujo de calibración y `PhysicalMapper` antes del encoder RGBIC.
- Diseñar después un encoder explícito de steps físicos a un slot probado y
  `elm`, distinguiendo transporte exitoso de efecto aplicado.
- Confirmar permiso/licencia antes de publicar atribuciones definitivas.
- Validar el comportamiento contra hardware RGBIC real sin acoplarlo a los
  modelos de efectos.
