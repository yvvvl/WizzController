# RGBIC hardware validation foundation

Status: Completed

Fecha: 2026-07-26

Actualizado con evidencia real: 2026-08-02

Rama: `feature/v1.3.0-effects-engine-foundation`

Relacionado:

- `docs/adr/0003-effects-engine-architecture.md`
- `docs/codex/PROJECT_CONTEXT.md`
- `docs/codex/queries/2026-08-02-09-rgbic-fixtures-model-correction-encoder.md`

## 1. Contexto

La validación ya no es sólo una preparación documental. Existe evidencia real
revisada de un tester comunitario con una tira RGBIC WiZ.

Dispositivo validado:

- `moduleName`: `ESP25_MHORGB_01`
- `fwVersion`: `1.38.0`
- instalación calibrada: 17 segmentos físicos
- tira original de 5 m cortada aproximadamente a 4 m

El hardware no pertenece al desarrollador. La observación visual sigue
dependiendo del tester, por lo que `success: true` no se interpreta como
confirmación visual por sí sola.

## 2. Evidencia confirmada

Se confirmó con hardware real que:

- RGBIC usa `setPilot`;
- `sceneId: 257` puede responder `success: true` y aun así ignorar `elm`,
  reproduciendo un efecto guardado del dispositivo;
- `sceneId: 258` respondió `success: true` y aplicó correctamente el patrón
  RGBIC observado en esta instalación;
- `sceneId: 256` permanece `untested`;
- `elm.modifier` es global y no pertenece a cada step;
- `elm.support` se observó con valor 17, igual a la calibración instalada,
  pero su semántica exacta sigue siendo experimental;
- cada step contiene exactamente 13 enteros;
- índices 1, 2 y 3 representan `red`, `green` y `blue`;
- índice 7 representa el brillo/dimming del step;
- índice 12 representa `width` físico absoluto;
- los demás índices del step permanecen en 0 y su significado sigue
  desconocido;
- se aceptan menos de 12 steps;
- el máximo confirmado para `ESP25_MHORGB_01` con firmware `1.38.0` es
  12 steps;
- 13 o más steps devuelven `{"error":{"code":-32602,"message":"Invalid params"}}`;
- `getPilot` no devuelve `elm`;
- `getSystemConfig` no devuelve longitud instalada ni cantidad de segmentos;
- la fórmula uniforme `[1,1,2,1,2,1,1,2,1,2,1,2]` cubre exactamente los
  17 segmentos calibrados;
- doce widths de 1 cubren 12 segmentos y dejan 5 apagados.

## 3. Payload sanitizado observado

```json
{
  "method": "setPilot",
  "params": {
    "mac": "<redacted>",
    "state": true,
    "sceneId": 258,
    "elm": {
      "modifier": 100,
      "support": 17,
      "steps": [
        [0, 255, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 1],
        [0, 0, 0, 255, 0, 0, 0, 100, 0, 0, 0, 0, 1]
      ]
    }
  }
}
```

La presencia de `mac` en esta captura no convierte ese campo en requisito del
encoder puro. La foundation interna de esta fase no lo incorpora.

## 4. Fixture model confirmado

Los fixtures reales sanitizados viven en `tests/fixtures/rgbic/`:

- `device-esp25-mhorgb-01-fw-1.38.0.json`
- `scene-257-occupied-success-visually-wrong.json`
- `scene-258-empty-success-visually-correct.json`
- `step-limit-fw-1.38.0.json`
- `width-coverage-17-segments.json`

Cada fixture separa:

- identidad técnica del dispositivo;
- payload;
- resultado de transporte;
- resultado visual;
- límites confirmados;
- campos todavía desconocidos.

## 5. Preguntas todavía abiertas

La evidencia actual no autoriza asumir:

1. que `sceneId: 258` sea universal para otros firmwares o dispositivos;
2. que `support` sea una API oficial para longitud física;
3. que los índices desconocidos del step deban recibir otro valor que 0;
4. que el dispositivo soporte escritura estable a 30 FPS productivos;
5. que `success: true` permita omitir confirmación visual.

No se recomienda probing automático silencioso al startup.

## 6. Decisiones derivadas

- tratar `modifier` como dato global de `elm`;
- tratar `brightness` y `width` como datos por step;
- mantener `support` como entero experimental;
- mantener `sceneId` fuera del modelo físico puro;
- validar visualmente cualquier estrategia de slots;
- no crear lookup tables `firmware -> sceneId`;
- no crear lookup tables `modelo -> segmentos`.

## 7. Criterio de uso futuro

Esta evidencia es suficiente para:

- corregir el modelo interno;
- crear fixtures reales sanitizados;
- crear un encoder puro a params de `setPilot`;
- mantener el transporte desconectado.

Todavía no es suficiente para:

- prometer soporte productivo RGBIC;
- declarar un slot universal;
- inferir visual success desde transporte;
- habilitar probing automático silencioso.
