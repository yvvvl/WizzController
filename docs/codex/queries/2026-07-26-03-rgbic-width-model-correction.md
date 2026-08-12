# RGBIC width model correction

Status: Completed

Fecha: 2026-07-26

Rama: `feature/v1.3.0-effects-engine-foundation`

Relacionado:

- `2026-07-26-02-rgbic-effects-foundation.md`
- `docs/adr/0003-effects-engine-architecture.md`

## 1. Contexto de la corrección

Después de crear la foundation de efectos, TechAntohere aportó información
adicional sobre el comportamiento RGBIC WiZ observado en
WizScreenSyncController. La nueva información cambia la semántica que se
había asignado a `width`/`weight`.

Esta fase corrige únicamente documentación y arquitectura. No modifica
modelos Python, `LightController`, `WizProtocol`, discovery ni UI. Tampoco
implementa scheduler, mapper, encoder o adapter RGBIC.

## 2. Supuesto anterior incorrecto

La foundation documentó y modeló `width`/`weight` como una proporción relativa
de zona. Bajo ese supuesto, las zonas lógicas del efecto y las unidades
físicas de salida quedaban representadas por el mismo concepto.

Esa interpretación es incorrecta y no debe guiar una integración con
hardware. El campo `RGBICZone.weight` existente conserva el nombre y la
validación creados en aquella fase, pero no representa un contrato físico
aprobado.

## 3. Modelo corregido: `width` es un span físico

Cada entrada de `elm.steps` es un step físico secuencial:

- contiene un color;
- `width` indica una cantidad absoluta de segmentos físicos;
- `width: 1` ocupa un segmento;
- `width: 2` ocupa dos segmentos;
- el siguiente step continúa después del span anterior, desde el inicio de la
  tira.

Ejemplos:

- 12 steps con `width: 1` cubren 12 segmentos físicos;
- 12 steps con `width: 2` cubren aproximadamente 24 segmentos físicos;
- 12 steps no garantizan cubrir toda la tira.

El límite observado de 12 steps describe la cantidad de entradas del payload,
no la longitud física del dispositivo.

El firmware no conoce necesariamente la longitud instalada. Una tira cortada
puede conservar el mismo identificador de modelo. La cobertura real depende
de densidad, longitud instalada y calibración. Por ello, no existe una
derivación segura `modelo -> cantidad fija de segmentos`.

## 4. Arquitectura corregida

```text
Effect Source (Screen Sync, Gradient, Music)
        |
Logical Effect Frame
        |
Physical Mapper  <---------------- Calibration Profile
        |
RGBIC Steps
        |
LightController
        |
WizProtocol
```

### Logical Effect Zones

Representan intención: izquierda, centro, derecha u otra región conceptual.
No contienen `width`, LEDs, segmentos, densidad ni campos WiZ.

### Physical RGBIC Steps

Representan salida física. Cada `RGBICStep` conceptual contiene color y
`width` absoluto. Su posición se deriva del orden secuencial.

### Calibration Layer

Describe la instalación concreta y permite resolver:

- cantidad utilizable de segmentos físicos;
- tiras cortadas;
- longitudes distintas;
- densidades diferentes;
- ajustes confirmados por el usuario.

El perfil pertenece al dispositivo/instalación, no a una tabla global por
modelo.

## 5. Impacto

### `RGBICFrame`

El modelo actual mezcla una lista de zonas con un `weight` cuya interpretación
original quedó obsoleta. No se modifica en esta fase, pero debe considerarse
provisional y no apto para encoding físico.

Una fase de código posterior debe decidir si:

- `RGBICFrame` pasa a representar exclusivamente steps físicos y adopta
  `RGBICStep.width`; o
- se reemplaza por tipos separados para frames lógicos y salida física.

La segunda opción preserva mejor el límite decidido en el ADR.

### Effects Engine

El engine produce intención lógica. No conoce longitud, densidad, segmentos,
`sceneId`, `elm`, UDP ni dispositivos WiZ concretos.

### Screen Sync

Screen Sync produce colores para regiones lógicas de la pantalla. No asigna
spans físicos. El mismo frame lógico puede mapearse de forma diferente para
dos instalaciones calibradas.

### Calibración

La calibración se vuelve requisito arquitectónico para una salida RGBIC
predecible. Debe existir antes de asumir cobertura total de una tira. Su flujo
de UX, persistencia y fallback seguro quedan pendientes de diseño.

## 6. Decisiones

No se debe:

- crear una lookup table fija por modelo;
- asumir segmentos por producto;
- inferir longitud instalada desde el límite de 12 steps;
- tratar `width` como proporción;
- mezclar zonas lógicas con segmentos físicos;
- poner mapping o encoding dentro de una fuente de efectos;
- permitir salida directa desde Effects Engine;
- hardcodear un `sceneId` o crear una tabla `firmware -> sceneId`;
- tratar éxito de transporte como prueba de efecto aplicado.

Se mantiene:

- `LightController` como único dueño de salida;
- `WizProtocol` como transporte genérico;
- efectos independientes de hardware y UI;
- slots seleccionados mediante capabilities, probing y fallback acotado;
- validación inicial mediante simuladores y tests.

## 7. Colaboración externa

Se registra a TechAntohere por los siguientes aportes conceptuales:

- investigación RGBIC;
- uso inicial observado de `sceneId: 257` y evidencia posterior de que 258
  puede ser necesario después de cambios de firmware/estado interno;
- contenedor `elm`;
- estructura secuencial de `elm.steps`;
- corrección del comportamiento físico de `width`;
- `modifier` experimental;
- diferencia entre transporte exitoso y efecto aplicado.

No se copió código de WizScreenSyncController. El texto definitivo de
créditos y el permiso/licencia de modificación y redistribución permanecen
pendientes de formalización.

## 8. Archivos documentales de esta fase

- `docs/codex/PROJECT_CONTEXT.md`
- `docs/archive/2026-07-26-new-chat-prompt.md`
- `docs/codex/queries/2026-07-26-01-screen-sync-review.md`
- `docs/codex/queries/2026-07-26-02-rgbic-effects-foundation.md`
- `docs/codex/queries/2026-07-26-03-rgbic-width-model-correction.md`
- `docs/adr/0003-effects-engine-architecture.md`
- `docs/third-party/2026-07-26-wizscreensynccontroller-review.md`
- `THIRD_PARTY_NOTICES.md` — sólo borrador interno

## 9. Validación

Alcance documental:

- revisar consistencia de términos y referencias;
- ejecutar `git diff --check`;
- confirmar con Git que no cambió código productivo.

Resultado:

- `git diff --check`: exit code 0, sin errores;
- la lista de cambios tracked contiene únicamente archivos Markdown;
- los archivos nuevos de esta fase están bajo `docs/`;
- no se alteró código productivo ni se ejecutó validación con hardware.

No se requieren tests de hardware en esta fase. La validación física se hará
cuando exista hardware compatible o mediante testers de la comunidad.

## 10. Próximos pasos

En fases separadas y sujetas a aprobación:

1. diseñar el flujo y formato persistido de calibración;
2. diseñar `PhysicalMapper` y sus fixtures simulados;
3. corregir los modelos Python conceptuales;
4. diseñar el encoder de `RGBICStep` a un slot probado/validado y
   `elm.steps`;
5. modelar probing, fallback acotado y resultado `effect applied`;
6. validar simuladores y tests de contrato;
7. validar después con hardware compatible o testers de la comunidad.
