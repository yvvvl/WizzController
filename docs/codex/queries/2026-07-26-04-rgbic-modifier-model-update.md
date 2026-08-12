# RGBIC modifier model update

Status: Completed

Fecha: 2026-07-26

Rama: `feature/v1.3.0-effects-engine-foundation`

Relacionado:

- `2026-07-26-03-rgbic-width-model-correction.md`
- `docs/adr/0003-effects-engine-architecture.md`

## 1. Contexto

TechAntohere aportó nueva información de ingeniería inversa sobre los steps
RGBIC WiZ. La corrección anterior estableció que `width` es un span físico
absoluto. La nueva observación añade que cada step también contiene un
`modifier`.

Esta fase actualiza contratos documentales. No modifica modelos Python ni
implementa scheduler, sesión realtime, mapper, encoder, UI, soporte de
hardware o cambios en `LightController`.

## 2. Información aportada por TechAntohere

El comportamiento observado es:

- cada step tiene color, `width` y `modifier`;
- `width` ocupa una cantidad absoluta de segmentos físicos consecutivos;
- los steps se aplican secuencialmente desde el inicio de la tira;
- `modifier: 100` corresponde a color estático;
- los valores 101–125 parecen corresponder a efectos internos usados por la
  app WiZ;
- existen otros rangos con comportamiento de efectos;
- la semántica exacta de todos los valores aún no está documentada.
- `sceneId: 257` funcionó inicialmente, pero después de una actualización de
  firmware pareció ser reemplazado por un efecto guardado;
- `sceneId: 258` permitió recuperar el comportamiento esperado;
- un comando transportado con éxito no garantiza que el efecto se aplique.

Estos datos son observaciones de ingeniería inversa, no una API oficial WiZ.
No se copió código de WizScreenSyncController.

## 3. Contrato conceptual actualizado

```text
Effect Source (Screen Sync, Gradient, Music)
        |
Logical Effect Frame
        |
Physical Mapper  <---------------- Calibration Profile
        |
RGBIC Steps (color + width + modifier)
        |
LightController
        |
Future RGBIC Encoder
        |
probed scene slot / elm.steps
        |
WizProtocol
```

El diagrama expresa responsabilidades, no nuevas clases productivas. El
encoder permanece dentro del límite de salida poseído por `LightController`;
no es una ruta paralela de control.

### Logical Effect Frame

Representa intención:

- regiones como izquierda, centro y derecha;
- regiones de pantalla;
- colores;
- orden lógico.

No conoce:

- LEDs o segmentos físicos;
- longitud o densidad de una tira;
- `width`;
- `modifier`;
- `sceneId`, `elm` o WiZ.

### Physical Mapper

Convierte intención lógica en salida física usando la calibración de una
instalación concreta. Produce steps ordenados, pero no serializa payloads ni
envía UDP.

Una política física futura podrá seleccionar el `modifier` apropiado. Esta
fase no define esa política ni asigna nombres a los valores observados.

### RGBICStep

El contrato físico futuro contiene conceptualmente:

- `color`;
- `width`: span físico absoluto;
- `modifier`: entero experimental;
- posición implícita por el orden secuencial.

`modifier` no es un enum. El valor 100 puede registrarse como estático según
la evidencia disponible; 101–125 y otros rangos permanecen experimentales.

### Calibration

La calibración pertenece a un dispositivo instalado y debe representar su
span físico utilizable. No se infiere mediante una lookup table por modelo,
porque cortes, longitud instalada y densidad pueden variar.

### Future RGBIC encoder

El encoder futuro recibe `RGBICStep` ya mapeados y los transforma en el
contenedor observado:

```text
RGBICStep[]
      |
validated scene slot
      |
elm.steps
```

El encoder:

- preserva `color`, `width` y el entero `modifier`;
- no interpreta regiones lógicas;
- no calcula calibración;
- no decide spans;
- no define enums de efectos;
- no hardcodea 257, 258 u otro slot;
- no selecciona un slot sólo por la versión de firmware;
- permanece detrás de `LightController`.

La capa de salida futura debe consultar capabilities, probar candidatos de
forma acotada, aplicar fallback y separar `transport success` de
`effect applied`.

## 4. Decisiones

- Mantener `LogicalEffectFrame` completamente independiente de RGBIC y WiZ.
- Mantener `width` como span físico absoluto.
- Mantener `modifier` como entero experimental.
- No crear enums, nombres estables ni una tabla exhaustiva de modifiers.
- No crear una tabla `modelo -> segmentos`.
- Resolver cobertura física mediante calibración por instalación.
- Mantener mapping y encoding como responsabilidades separadas.
- Mantener `LightController` como único dueño de salida.
- Mantener slots/contenedores como datos probados, no constantes.
- No crear una tabla `firmware -> sceneId`.
- Validar el efecto aplicado además del resultado de transporte.

## 5. Impacto

### Foundation actual

`RGBICZone.weight` y `RGBICFrame` no representan todavía el contrato físico
corregido. Carecen de `width` explícito y de `modifier`. Siguen siendo
scaffolding estructural y no deben conectarse a hardware.

La foundation permanece correcta en inmutabilidad, simulación, transporte
genérico y separación de UI/UDP. Esta actualización amplía sólo el contrato
físico futuro.

No se corrigen los modelos Python en esta fase.

### Effects Engine

El engine conserva su independencia de hardware. Las fuentes de efectos
producen intención lógica y no eligen modifiers internos de WiZ.

### Physical mapping

El mapper futuro necesita calibración y una política de salida comprobable.
Debe poder probarse con fixtures y simuladores antes de usar hardware.

### Encoder

El encoder futuro debe ser mecánico: serializa steps físicos ya resueltos. La
interpretación incompleta de modifiers no debe filtrarse hacia el frame
lógico ni convertirse prematuramente en una API pública. La selección de
contenedor pertenece a la salida capability-aware y debe admitir probing y
fallback acotados.

## 6. Pendientes

En fases separadas:

1. capturar fixtures representativos de `modifier`;
2. confirmar con hardware o testers comunitarios el comportamiento de 100;
3. investigar 101–125 y otros rangos sin prometer nombres estables;
4. diseñar el flujo y formato persistido de calibración;
5. diseñar `PhysicalMapper` y sus simuladores;
6. corregir los modelos Python conceptuales;
7. diseñar y probar el encoder de `RGBICStep` a `elm.steps`;
8. diseñar probing/fallback de slots y validación de `effect applied`;
9. diseñar scheduler y sesión realtime sólo después de aprobar sus contratos.

## 7. Archivos documentales

- `docs/adr/0003-effects-engine-architecture.md`
- `docs/codex/PROJECT_CONTEXT.md`
- `docs/codex/queries/2026-07-26-04-rgbic-modifier-model-update.md`

## 8. Validación

- revisar que `modifier` sólo pertenezca al modelo físico;
- verificar que no se haya creado un enum ni una tabla por modelo;
- ejecutar `git diff --check`;
- confirmar mediante `git status` que no cambió código productivo.

No se realiza validación física en esta fase. El hardware se validará cuando
haya dispositivos compatibles o mediante testers de la comunidad.
