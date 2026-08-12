# RGBIC logical compression, experimental hardware bridge and beta validator

Status: Completed

Fecha: 2026-08-03

Rama: `feature/v1.3.0-effects-engine-foundation`

Relacionado:

- `docs/adr/0003-effects-engine-architecture.md`
- `docs/codex/PROJECT_CONTEXT.md`
- `docs/codex/queries/2026-07-26-07-rgbic-hardware-validation.md`
- `docs/codex/queries/2026-08-02-09-rgbic-fixtures-model-correction-encoder.md`

## 1. Objetivo

Corregir la separación entre límite lógico y límite físico RGBIC, añadir una
compresión lógica determinista para respetar el máximo físico observado, y
crear una base experimental mínima para validación con hardware real usando el
camino oficial `LightController`/`WizProtocol`.

La fase no crea soporte RGBIC productivo. No introduce scheduler, streaming
realtime, UI definitiva, autodetección de slot ni selección automática de
capabilities RGBIC.

## 2. Corrección de modelo

La evidencia acumulada ya no permite tratar el límite observado de 12 como si
fuera un límite del frame lógico.

Decisiones:

- `MAX_RGBIC_PHYSICAL_STEPS = 12` representa el techo físico confirmado del
  programa/payload RGBIC;
- `EffectFrame` deja de capar zonas lógicas en 12 y sólo exige ids positivos y
  únicos;
- `RGBICFrame` representa intención lógica compresible y puede contener más de
  12 colores;
- cuando una fuente lógica produce más de 12 colores/regiones, primero debe
  aplicarse compresión determinista y recién después mapping físico.

## 3. Compresión lógica

Se añadió `compress_rgbic_colors(colors, max_steps=12)` en
`core/effects/rgbic_mapper.py`.

Propiedades:

- pura y determinista;
- preserva el orden lógico;
- agrupa regiones contiguas;
- promedia canales RGB por grupo;
- no conoce `sceneId`, `elm`, UDP ni hardware.

Esto mantiene la separación:

- intención lógica amplia;
- límite físico acotado;
- mapping físico posterior sobre calibración real.

## 4. Modelo y contratos actualizados

Cambios conceptuales reflejados en código y tests:

- `RGBICStep` conserva `color`, `width` y `brightness` opcional;
- `RGBICProgram` sigue siendo el dueño de `steps`, `modifier` global y
  `support`;
- `DeviceCapabilities` reemplaza el antiguo dato ambiguo de zonas por
  `rgbic: bool` y `rgbic_max_steps: int | None`;
- `RGBICTransportResult` separa:
  - `transport_status`
  - `visual_status`
  - `transport_error`

Esto formaliza que `success: true` en transporte no equivale a validación
visual del efecto aplicado.

## 5. Experimental hardware bridge

Se añadió un puente experimental mínimo:

- `LightController.send_rgbic_program(...)`

Características:

- usa el camino oficial `LightController` -> `WizProtocol`;
- exige `scene_id` explícito y tipado;
- realiza un envío único, no streaming;
- serializa mediante el encoder puro existente;
- preserva payloads WiZ de error como `-32602`;
- deja `visual_status = \"unconfirmed\"` aunque el transporte sea aceptado.

No implementa:

- scheduler;
- realtime session;
- fallback automático de slots;
- probing automático;
- soporte estable para usuarios finales.

## 6. Beta validator

Se añadió `tools/rgbic_beta_validator.py`.

Responsabilidades:

- generar patrones lógicos controlados;
- comprimir si exceden el máximo físico;
- mapear a steps físicos según calibración;
- enviar una prueba única por el bridge experimental;
- pedir confirmación visual manual;
- guardar artefactos sanitizados en `artifacts/rgbic-validation/`.

La sanitización elimina IP/MAC de payloads y notas antes de persistir.

## 7. Archivos

Modificados:

- `core/effects/__init__.py`
- `core/effects/models.py`
- `core/effects/rgbic_mapper.py`
- `core/effects/rgbic_simulator.py`
- `core/light_controller.py`
- `core/wiz_protocol.py`
- `tests/test_effect_models.py`
- `tests/test_rgbic_mapper.py`
- `tests/test_rgbic_simulator.py`
- `tests/test_rgbic_bridge.py`
- `tests/test_rgbic_beta_validator.py`
- `docs/adr/0003-effects-engine-architecture.md`
- `docs/codex/PROJECT_CONTEXT.md`

Creados:

- `core/effects/rgbic_encoder.py`
- `tools/rgbic_beta_validator.py`
- `tests/test_rgbic_encoder.py`
- `docs/codex/queries/2026-08-03-10-rgbic-beta-hardware-bridge.md`

## 8. Riesgos y límites

- el bridge es experimental y no implica soporte RGBIC estable;
- `sceneId` sigue siendo dato runtime/fixture, no constante protocolaria;
- `modifier` sigue siendo entero experimental;
- streaming beta se pospone a una fase posterior;
- la validación visual sigue dependiendo de hardware y confirmación humana.

## 9. Validación ejecutada

Resultados ejecutados el lunes 3 de agosto de 2026:

- `.venv\Scripts\pytest.exe -q`
  - resultado: `318 passed, 98 warnings`
  - failed: `0`
  - skipped: `0`
  - exit code: `0`
- `.venv\Scripts\python.exe -m compileall -q main.py app_meta.py core config ui localization tests tools`
  - exit code: `0`
- `.venv\Scripts\python.exe tools/i18n_audit.py`
  - resultado: `Catalogs OK: 579 keys · en/es`
  - resultado adicional: `Potential hardcoded UI strings: 0`
  - exit code: `0`
- `git diff --check`
  - resultado: sin errores de whitespace
  - exit code: `0`
- `.venv\Scripts\python.exe tools\rgbic_beta_validator.py --help`
  - no se pudo ejecutar como help seguro
  - el revisor de seguridad rechazó la ejecución porque el script no implementa
    `--help` y aun así iniciaría `LightController`, provocando discovery local
    y actividad de red
  - no se intentó un workaround que enviara tráfico adicional o alcanzara el
    paso de envío RGBIC

Estado funcional confirmado:

- compresión lógica determinista: implementada
- `CalibrationProfile`: implementado
- `RGBICStep`: implementado
- `RGBICProgram`: implementado
- encoder puro: implementado
- bridge experimental detrás de `LightController`: implementado
- beta validator: implementado
- streaming: aplazado
- soporte productivo RGBIC: inexistente

## 10. Comando real para el tester

El comando real para el tester es:

- `.venv\Scripts\python.exe tools\rgbic_beta_validator.py`

El script es interactivo. No usa `--help` y no debe considerarse seguro como
comando autodocumentado.

Por inspección del flujo actual:

- iniciar el script por sí solo no envía RGBIC inmediatamente;
- primero pide `physical_segments`;
- después pide `sceneId`;
- después pide `pattern`;
- el envío ocurre sólo después de recibir esos datos y construir el programa.

## 11. Instrucciones listas para copiar al tester

1. Abre una terminal dentro del repo `WizzController`.
2. Asegúrate de tener la virtualenv del proyecto disponible en `.venv`.
3. Ejecuta:
   `.venv\Scripts\python.exe tools\rgbic_beta_validator.py`
4. Cuando el script pida `physical_segments`, introduce:
   `17`
5. Cuando pida `sceneId`, introduce un slot manual sugerido para comenzar,
   por ejemplo `258`.
   - esto es sólo dato manual de arranque;
   - no está hardcodeado;
   - si ese slot no aplica visualmente, no significa que otro firmware use el
     mismo.
6. Cuando pida `pattern`, elige uno de estos:
   - `red_blue_split`
   - `rgb_repeat`
   - `rainbow_gradient`
   - `uniform_coverage`
   - `twelve_step_test`
7. Observa el resultado visual real en la tira y responde:
   - `confirmed_correct` si coincide;
   - `confirmed_wrong` si el dispositivo acepta transporte pero el efecto es
     incorrecto;
   - `unconfirmed` si no hay certeza.
8. Escribe notas breves al final:
   - firmware;
   - comportamiento visual;
   - si pareció usar un efecto guardado;
   - cualquier diferencia relevante.

Notas operativas:

- no escribas la IP en el archivo final de devolución;
- si necesitas usar una IP local para tu prueba, introdúcela sólo dentro de tu
  entorno local y no la compartas en el artefacto entregado;
- el artefacto generado queda en:
  `artifacts/rgbic-validation/`
- el archivo a devolver es el JSON recién generado en esa carpeta;
- para detenerte sin ejecutar otro slot, cierra el script después de la prueba
  y no vuelvas a lanzarlo con otro `sceneId` hasta revisar el resultado;
- `success: true` no confirma que el efecto se haya aplicado correctamente:
  sólo confirma transporte/aceptación del comando.
