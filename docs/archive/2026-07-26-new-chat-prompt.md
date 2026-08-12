# Prompt de continuidad para un nuevo chat

Status: Archived

Archivado porque `docs/codex/PROJECT_CONTEXT.md` y
`docs/codex/DOCUMENTATION_GUIDE.md` pasan a ser las fuentes canónicas de
continuidad y clasificación documental.

Estoy continuando el desarrollo de WizZ Desktop. Usa este documento como
contexto principal y lee completo `docs/codex/PROJECT_CONTEXT.md` antes de
proponer o realizar cambios. Contrasta siempre el contexto con la rama activa,
`git status`, `git log` y los reportes de `docs/codex/queries/`; no asumas que
una feature está integrada en `main` sólo porque exista en otra rama.

## Proyecto

WizZ Desktop es una aplicación Flet para Windows que controla luces WiZ
localmente por UDP LAN. Busca ofrecer control rápido, privado y fiable mediante
la Main App, Color Studio, favoritos, rutinas, hotkeys, tray y Quick Panel. La
visión futura incluye Effects Engine, RGBIC, Screen Sync, Home Assistant, más
plataformas y plugins.

La versión estable es `v1.1.0`. El desarrollo declarado actual es Quick Panel
v1.2. Su foundation y su rediseño Premium están implementados, pero no deben
considerarse release cerrada hasta completar la validación manual de tray,
ventana, hardware y plataformas.

Al crear este contexto, el checkout estaba en
`feature/v1.3.0-effects-engine-foundation`, commit `0a09163`. Esa rama incluye
modelos y un simulador experimental de efectos/RGBIC sobre el Quick Panel
Premium. No existe todavía un Effects Engine productivo, scheduler, sesión
realtime, Screen Sync, Gradient, adapter RGBIC de hardware ni UI de efectos.

Ramas/commits relevantes:

- `main` / tag `v1.1.0`: `0a902d0`;
- `release/v1.1.0`: `50a4b84`;
- Quick Panel foundation: `ea1cc0e` en la historia actual y rama
  `feature/v1.2.0-quick-panel` en `1838eca`;
- Quick Panel Premium: rama `feature/v1.2.0-quick-panel-design`, commit
  `ec9da58`;
- effects/RGBIC foundation: rama
  `feature/v1.3.0-effects-engine-foundation`, commit `0a09163`.

## Arquitectura que debes respetar

El flujo de control es:

```text
Main UI / Quick Panel / Tray / Hotkeys / Favoritos / Rutinas
                              |
                              v
                   ActionSequenceExecutor
                              |
                              v
                      LightController
                              |
                              v
                       WizProtocol
                              |
                              v
                  UDP LAN WiZ :38899
```

Responsabilidades:

- `LightController` es la única fachada de iluminación. Posee discovery,
  targeting, estado, capacidades, control, coalescing y coordinación de red.
- `WizProtocol` es la única capa UDP. `send_pilot()` usa `setPilot`
  fire-and-forget; las lecturas quedan fuera del hot path.
- `ActionSequenceExecutor` ejecuta acciones discretas de rutinas, favoritos,
  hotkeys y tray. No debe transportar frames realtime.
- `FavoritesManager` es la fuente del contrato persistido de favoritos:
  RGB/HEX, White/Kelvin, Scene y Brightness.
- `TrayService` posee lifecycle y acciones de bandeja, y agenda trabajo hacia
  Flet sin implementar lógica WiZ.

No crees un segundo controlador, un segundo discovery, otro executor, otro
almacén de favoritos ni sockets UDP en features. Los módulos protegidos no se
modifican de forma incidental:

- `core/light_controller.py`;
- `core/wiz_protocol.py`;
- `core/action_sequence.py`;
- `config/favorites_manager.py` y `favorites.json`;
- `ui/color_studio.py`;
- `ui/components/color_panel.py`;
- sistema y catálogos i18n.

Si la tarea requiere ampliar uno de esos contratos, detente antes de editarlo,
explica la razón, el alcance, el diseño y los tests necesarios.

## UI y Quick Panel

La Main App usa Flet. Existe una sola `Page`, una sola ventana y un solo
`LightController`. Main App y Quick Panel alternan contenido dentro de un host
compartido.

Quick Panel se compone de:

- `QuickPanelController`: snapshots, targeting, comandos y modos
  hidden/quick/full;
- `QuickPanelView`: shell Premium por cards;
- `ColorStudioQuickAdapter`: composición compacta de controles existentes;
- `TrayService`: clic simple, doble clic y menú contextual.

El diseño Premium tiene cards de header/dispositivo, power, target, Color
Studio y hasta seis favoritos. En Windows usa un overlay de `440 x 680`,
always-on-top, no redimensionable y situado a 16 px de la esquina inferior
derecha del área de trabajo bajo el cursor. Debe restaurar todas las
propiedades de la ventana al volver a la aplicación completa.

Color Studio es la fuente de verdad. El adapter sólo monta el subárbol activo
de Color o White y reutiliza picker, Hue/Purity, HEX/RGB, quick colors,
conversión WiZ, Kelvin, brightness, throttling, guardas y controles de
aplicación. No copies ni reimplementes matemática o UI interna de Color
Studio.

Pendientes manuales de Quick Panel:

- abrir/ocultar, doble clic, menú derecho y restauración;
- foco y ventana frameless;
- Color/White, ON/OFF, favoritos y targeting con hardware;
- fidelidad RGB y límites Kelvin;
- monitor bajo cursor, DPI mixto y varios monitores;
- X11 y AppIndicator/Wayland.

El siguiente objetivo de producto es terminar y validar profesionalmente
Quick Panel v1.2 antes de declarar su release.

## Screen Sync y RGBIC

Se investigó el repositorio externo
`TechAntohere/WizScreenSyncController`, revisión
`0feb5749a28389bc6971639467f6cb7fd464ebe2`. El autor reportado es
TechAntohere. Existe un permiso reportado, pero el repositorio no tiene
licencia y el alcance de modificación/redistribución debe formalizarse con
evidencia escrita. El permiso/licencia y los créditos definitivos siguen
pendientes.

Regla: **no copies código de ese repositorio**. Adapta sólo conceptos mediante
una implementación propia y modular. No incorpores su UI PyQt6, discovery,
tray, persistencia ni sockets.

Hallazgos técnicos:

- RGBIC usa `setPilot`;
- 257 y 258 se observaron como contenedores en estados distintos; ningún
  `sceneId` es una constante;
- `elm` contiene datos dinámicos;
- `elm.steps` contiene steps físicos secuenciales, no zonas lógicas;
- se observaron hasta 12 steps por payload, sin que eso determine la longitud
  física de la tira;
- `width` es un span absoluto: 1 ocupa un segmento físico, 2 ocupa dos, etc.;
- una tira cortada puede conservar el mismo modelo y el firmware no conoce
  necesariamente la longitud instalada;
- no se debe crear una tabla fija `modelo -> cantidad de segmentos`.
- tampoco se debe crear una tabla `firmware -> sceneId` ni confundir éxito de
  transporte con efecto aplicado.

Son observaciones no oficiales. Requieren fixtures, capabilities y hardware
real antes de convertirse en comportamiento productivo.

Screen Sync debe ser una fuente pura que produzca frames lógicos. No puede
importar sockets, `WizProtocol`, Flet ni Qt ni decidir spans físicos. Debe
usar `latest wins`, rate limiting, deduplicación, ownership y errores
visibles. La recomendación es empezar con un MVP Windows de una zona por
bombilla y validar Linux/Wayland y RGBIC en fases separadas.

## Effects Engine

`core/effects/` ya contiene la foundation:

- `RGBColor`;
- `EffectFrame`;
- `RGBICZone`;
- `RGBICFrame`;
- `DeviceCapabilities`;
- simulador puro de 12 entradas modeladas como zonas; no representa longitud
  ni cobertura física.

`RGBICZone.weight` fue creado bajo el supuesto ahora corregido de una
proporción relativa. El modelo y el simulador no son un contrato físico y no
deben conectarse a hardware antes de separar intención y salida.

La arquitectura futura obligatoria es:

```text
Effect Source (Screen Sync, Gradient, Music)
      |
Logical Effect Frame
      |
Physical Mapper  <---------------- Calibration Profile
      |
RGBIC Steps (color + width absoluto)
      |
LightController
      |
WizProtocol
```

Las zonas lógicas expresan intención —por ejemplo, izquierda, centro y
derecha— y no conocen LEDs ni segmentos. El mapper usa una calibración por
instalación para resolver steps físicos secuenciales. Effects nunca debe
mandar UDP directamente y `LightController` sigue siendo el único dueño de la
salida.

El trabajo pendiente es diseñar el scheduler, una sesión realtime en
`LightController`, el flujo de calibración, `PhysicalMapper`, el encoder de
steps a `sceneId`/`elm`, capabilities RGBIC y validación con hardware.

## `pywizlight`

La dependencia actual es `pywizlight==0.6.3`. Se usa para discovery y
capacidades complementarias y para conversión de color; el control frecuente
continúa en UDP nativo. No introduzcas llamadas de `pywizlight` en sliders,
drag de Color Studio, hotkeys, tray, rutinas o efectos.

Existe intención de contactar a los desarrolladores de `pywizlight` por
posible soporte RGBIC, pero no debes contactarlos hasta tener una
implementación reproducible, fixtures, evidencia de hardware e identificación
de capabilities. No mezcles esa conversación con un upgrade de dependencia.

## Decisiones que no debes revertir fácilmente

- no duplicar lógica WiZ;
- no crear controladores paralelos;
- Color Studio es la fuente de verdad;
- usar capabilities en vez de suposiciones por modelo o estado activo;
- todo UDP pasa por `LightController`/`WizProtocol`;
- `ActionSequenceExecutor` es para acciones discretas, no frames;
- conservar una ventana, una instancia y un `LightController`;
- reutilizar managers, formatos persistidos e i18n;
- documentar autor, revisión, permiso/licencia y créditos de colaboraciones;
- no copiar WizScreenSyncController;
- aislar upgrades, cambios de protocolo y refactors.

## Forma de trabajar

Antes de actuar:

1. lee `docs/codex/PROJECT_CONTEXT.md` y el reporte de query relacionado;
2. muestra y evalúa `git status`, rama y commits recientes;
3. identifica cambios preexistentes del usuario y no los sobrescribas;
4. confirma el alcance exacto y los límites protegidos.

Durante el trabajo:

- trabaja por rama;
- usa tests focalizados y luego la suite proporcional al riesgo;
- crea un reporte nuevo en `docs/codex/queries/`;
- no hardcodees copy visible; usa i18n;
- no mezcles features, upgrades ni refactors no solicitados;
- registra decisiones, archivos, validaciones y riesgos manuales.

Antes de terminar:

- ejecuta `git diff --check`;
- revisa `git diff`, `git status` y tests;
- distingue tests automatizados de validación manual;
- documenta commits y pendientes;
- no hagas merge, commit ni push sin autorización explícita.

## Próximos pasos recomendados

1. Inspeccionar el estado real de la rama que se vaya a continuar.
2. Completar la matriz manual del Quick Panel Premium.
3. Corregir sólo problemas observados, manteniendo los límites protegidos.
4. Volver a ejecutar tests, i18n, smoke de aplicación y validación Git.
5. Decidir la integración/release de Quick Panel v1.2.
6. Revisar separadamente la foundation de efectos de `0a09163`.
7. Diseñar el Effects Engine y su contrato realtime antes de añadir Screen
   Sync, Gradient o salida RGBIC.

No empieces nuevas features ni cambies arquitectura sólo por leer este prompt.
Espera la tarea concreta, inspecciona el repositorio y conserva estas
decisiones como restricciones de continuidad.
