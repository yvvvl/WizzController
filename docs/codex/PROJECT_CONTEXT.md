# WizZ Desktop — contexto maestro del proyecto

Última actualización: 2026-08-28

## Nota de auditoría del checkout actual

`v1.2.0` fue publicado desde `90f05d0` y fusionado en `main` mediante PR #8 en
`7eda835`. Windows es el canal estable y Linux x64 continúa etiquetado como
beta. La próxima fase pública es el refactor UI v1.3 descrito en
`docs/codex/plans/2026-08-28-v1.3-ui-refactor-and-branch-cleanup.md`, con su
proceso visual y de implementación detallado en
`docs/codex/plans/2026-08-28-v1.3-ui-design-execution-plan.md`.

La rama ya incorpora targeting transitorio `single`/`selected`/`all`, consulta
read-only de GitHub Releases, persistencia empaquetada fuera del directorio de
la aplicación y la frontera multiplataforma aprobada. Las builds Windows
guardan los datos del usuario en `%LOCALAPPDATA%\\WizZDesktop`, incluso cuando
Flet expone `FLET_APP_STORAGE_DATA`; no se deben incluir JSON reales en el
artefacto. Las instalaciones Flet anteriores se migran desde su ubicación
legacy al primer arranque.

Linux tiene una beta nativa validada en Ubuntu 22.04 GNOME/Wayland: wiring
productivo, paquete e instalador por usuario, tray AppIndicator, persistencia
XDG/autostart y control WiZ LAN. Los hotkeys globales permanecen deshabilitados
intencionalmente por seguridad. macOS está diferido. RGBIC continúa como beta
cerrada experimental; no forma parte del soporte público estable.

Este documento es la fuente principal de continuidad para nuevas sesiones de
ChatGPT/Codex. Antes de modificar el proyecto, se debe leer completo y
contrastar la rama activa, `git status`, los commits recientes y los reportes
de `docs/codex/queries/`. La clasificación y el ciclo de vida de documentos se
definen en `docs/codex/DOCUMENTATION_GUIDE.md`.

## 1. Resumen del proyecto

**WizZ Desktop** es una aplicación de escritorio para controlar luces WiZ
desde Windows y Linux mediante la red local. La aplicación principal está construida
con Flet y reúne control de iluminación, Color Studio, escenas, favoritos,
rutinas, hotkeys globales, bandeja del sistema y administración de
dispositivos.

El objetivo es ofrecer un control rápido, privado y fiable que no dependa de
la nube de WiZ para las acciones normales. El camino de control usa UDP LAN
nativo y `setPilot` fire-and-forget; las lecturas, verificaciones de estado y
capacidades permanecen fuera del camino de baja latencia.

El proyecto resuelve varios problemas de la experiencia de escritorio:

- control local aunque Internet no esté disponible;
- acceso rápido desde hotkeys compatibles y la bandeja del sistema;
- una única representación de acciones para UI, favoritos y rutinas;
- reproducción de color adaptada a los canales físicos RGBTW de WiZ;
- descubrimiento y selección de dispositivos sin depender de una cuenta
  remota;
- distribución portable para Windows y beta instalable por usuario en Linux.

La visión futura es convertir WizZ Desktop en una plataforma extensible de
iluminación local: Quick Panel profesional, Effects Engine, RGBIC, Screen
Sync, integración con Home Assistant, más plataformas y plugins. Esa
evolución debe conservar una sola ruta de control y evitar que cada feature
implemente su propio protocolo, discovery o controlador.

## 2. Estado actual

### Versiones y fase de desarrollo

- **Versión pública:** `v1.2.0`, Windows estable + Linux beta, tag en
  `90f05d0` e integrada en `main` mediante `7eda835`.
- **Desarrollo principal declarado:** limpieza segura de ramas y refactor UI
  v1.3 compartido entre Windows y Linux.
- **Estado de Quick Panel:** retirado de la composición activa de v1.2.0 tras
  fallos reales de geometría y foco. La bandeja restaura únicamente la ventana
  principal. Su código experimental queda fuera del flujo público hasta que
  exista una implementación independiente y validada.
- **Targeting:** selección transitoria de una, varias o todas las luces
  implementada y cubierta por tests; no requiere grupos persistentes.
- **Fixture DEV de múltiples luces:** `WIZZ_DEV_VIRTUAL_BULBS=<1..12>` permite
  ejecutar la app desde código fuente con ampolletas RGBTW virtuales, sin UDP
  ni persistencia de dispositivos falsos. Sirve para validar targeting, estado
  y controles sin hardware múltiple. El repaint continuo de escenas dinámicas
  en Flet 0.85.2 es irregular; no debe usarse como evidencia de fades reales.
- **Actualizaciones:** selección de canal y cliente GitHub read-only
  implementados, con comprobación manual visible en Ajustes y enlace validado
  a la release oficial. Todavía no existe descarga, instalación, reinicio ni
  rollback automático.
- **Persistencia empaquetada:** validada en
  `%LOCALAPPDATA%\\WizZDesktop`; los datos sobreviven al reemplazo del build y
  la carpeta Flet legacy se migra sin borrar su origen.
- **Foundation experimental adicional:** la base interna de efectos y RGBIC
  ya separa frame lógico, compresión lógica, calibración, steps físicos,
  mapper puro, simulador por segmentos y encoder puro. También existe un
  puente experimental de envío único mediante `LightController` y una
  herramienta beta de validación manual. Esto no equivale a un Effects Engine
  productivo: no hay scheduler, sesión realtime, Screen Sync, Gradient,
  soporte RGBIC estable, UI RGBIC definitiva ni selección automática de slot.
- **RGBIC validation status:** existe un tester comunitario con hardware RGBIC
  WiZ disponible para pruebas controladas. El hardware no pertenece al
  desarrollador; ya existen fixtures sanitizados y evidencia revisada para un
  dispositivo, además de un validador beta local para registrar nuevos casos.
  Esto sigue sin equivaler a soporte productivo.
- **Linux beta:** contratos y servicios están conectados al runtime; Ubuntu
  validó build nativa, tray AppIndicator, persistencia XDG, autostart y WiZ
  LAN. Los hotkeys Wayland no están resueltos y se muestran como no
  disponibles. macOS está explícitamente diferido.

### Ramas relevantes

| Rama | Estado y propósito |
| --- | --- |
| `main` | Línea canónica; contiene PR #8 y la release pública v1.2.0 |
| `feature/v1.3.0-ui-foundation` | Rama corta activa para documentación y fundación UI v1.3 |

La limpieza del 2026-08-28 dejó `main` como única rama remota permanente. La
historia divergente de Color Studio y el prototipo Quick Panel se conservan en
los tags `archive/color-studio-v2-legacy` y
`archive/quick-panel-flet-spike`; no deben fusionarse directamente.

### Últimos commits importantes

| Commit | Importancia |
| --- | --- |
| `7eda835` | merge de la release v1.2.0 en `main` mediante PR #8 |
| `90f05d0` | commit etiquetado `v1.2.0`; valida el instalador Linux en CI |
| `a376e3a` | añade instalador/desinstalador Linux y lanzador de aplicaciones |
| `84d4b8d` | integra la beta Linux aprobada en la rama de release |
| `72656ad` | estabiliza dependencias y pruebas Linux en CI |

### Features terminadas en la versión estable

- control LAN WiZ: power, brillo, RGB, Kelvin y escenas;
- Color Studio calibrado, controles precisos y aplicación en vivo o manual;
- targeting individual o de todas las luces disponibles;
- favoritos tipados y editor según capacidades;
- rutinas y acciones compuestas mediante `ActionSequenceExecutor`;
- hotkeys globales;
- tray con acciones rápidas, cierre a bandeja y restauración de ventana;
- instancia única;
- discovery híbrido, adición manual, renombrado y eliminación persistente;
- interfaz en español e inglés;
- build portable Windows con atribuciones de terceros.

## 3. Arquitectura actual

### Flujo principal

```text
Main UI / Tray / Hotkeys / Favoritos / Rutinas
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

### `LightController`

Archivo: `core/light_controller.py`.

Es el controlador central y la única fachada de iluminación que deben usar la
UI y los servicios de aplicación. Sus responsabilidades incluyen:

- ciclo asyncio en un thread dedicado;
- discovery WiZ y caché de dispositivos;
- targeting `single`, `selected` o `all`;
- estado lógico reflejado hacia la UI;
- control de power, brillo, RGB, Kelvin, escenas y favoritos;
- coalescing del camino de escritura;
- envío por medio de `WizProtocol`;
- polling de estado y verificaciones posteriores fuera del hot path;
- capacidades y rangos Kelvin por dispositivo;
- protección contra reaparición de dispositivos eliminados.

Es crítico porque concentra targeting, estado, lifecycle de red y envío. No se
deben crear controladores paralelos para Quick Panel, Screen Sync, RGBIC o
efectos.

### `WizProtocol`

Archivo: `core/wiz_protocol.py`.

Es la capa de transporte UDP LAN. Mantiene un socket reutilizable para
discovery, lecturas y control. `send_pilot()` serializa parámetros genéricos en
`setPilot` y envía sin esperar ACK; las consultas usan timeouts y retries
controlados.

Es crítico porque constituye la única salida de red WiZ. Ningún efecto,
componente UI o integración futura debe abrir su propio socket UDP.

### `ActionSequenceExecutor`

Archivo: `core/action_sequence.py`.

Es el motor único de acciones discretas para rutinas, hotkeys, favoritos y
tray. Normaliza y ejecuta power, targeting, brillo, RGB, Kelvin, escenas,
esperas, favoritos, rutinas y escenas personalizadas. Normalmente trabaja en
un thread para no bloquear la UI y serializa secuencias para impedir que dos
rutinas se mezclen.

No es un transporte de frames realtime. Puede iniciar o detener un efecto
futuro, pero no debe procesar cada frame de Screen Sync.

### `FavoritesManager`

Archivo: `config/favorites_manager.py`.

Administra el CRUD y la persistencia JSON de favoritos. El contrato estable
por item contiene `id`, `name`, `type`, `value`, `icon` y timestamps. Tipos
vigentes:

- `rgb`: HEX;
- `white`: Kelvin;
- `scene`: `sceneId` y `speed` opcional;
- `brightness`: porcentaje.

El formato persistido es compartido por Main App, Quick Panel, tray, hotkeys y
rutinas. No crear otro almacén de favoritos ni cambiar el JSON sólo para una
vista.

### `TrayService`

Archivo: `core/background/tray_service.py`.

Es el wrapper de integración con el system tray. Posee el lifecycle de
`pystray`, el menú contextual, mostrar/ocultar/salir, coordinación de clic
simple y doble clic, actualización localizada y scheduling seguro hacia el
loop de Flet. Ejecuta acciones mediante `ActionSequenceExecutor`; no manipula
internamente paneles Flet ni implementa lógica WiZ propia.

### Módulos críticos y límites protegidos

Los siguientes límites fueron explícitamente protegidos durante Quick Panel y
no deben modificarse de forma incidental:

- `core/light_controller.py`;
- `core/wiz_protocol.py` y la implementación del protocolo WiZ;
- `core/action_sequence.py`;
- `config/favorites_manager.py` y el formato de `favorites.json`;
- internals de Color Studio en `ui/color_studio.py` y
  `ui/components/color_panel.py`;
- sistema y catálogos existentes de localización.

Estos límites pueden evolucionar sólo en una fase aprobada, con una razón
arquitectónica concreta, tests y alcance aislado. Si una feature parece
necesitar saltárselos, detener la implementación y explicar primero la
expansión de alcance.

### Frontera cross-platform

ADR 0004 establece un único producto con integraciones de escritorio
capability-driven. `core/platform/` contiene la frontera compartida y los
servicios Linux todavía aislados del runtime principal:

- `CapabilityStatus` expresa `available`, `unavailable`, `degraded` o
  `permission_required`;
- `CapabilityState` agrega un motivo opcional y define si una capacidad es
  utilizable;
- `DesktopCapabilities` es un snapshot inmutable con estados independientes
  para hotkeys, tray, autostart, ventanas, instancia única y apertura de
  carpetas;
- `contracts.py` define `Protocol` neutrales para `HotkeyService`,
  `TrayBackend`, `AutostartService`, `WindowService`,
  `SingleInstanceService` y `SystemIntegrationService`;
- `fakes.py` implementa esos contratos con estado in-memory para tests.

`degraded` sigue siendo utilizable; `unavailable` y
`permission_required` no ejecutan la operación simulada. Exclusión y
activación de instancia única son capacidades distintas.

Ningún consumidor existente usa todavía esta frontera. El comportamiento
Windows continúa en sus módulos actuales y no fue movido ni modificado. Esta
foundation no demuestra soporte Linux por sí sola; macOS está fuera del
alcance operativo actual.

## 4. UI actual

### Estado

- La Main App usa **Flet**.
- Existe una sola `Page` y una sola ventana nativa.
- La aplicación pública usa la Main App como única superficie de ventana.
- La bandeja restaura la ventana completa; Quick Panel no está compuesto en
  el runtime v1.2.0.
- La foundation y el diseño histórico del Quick Panel se conservan sólo como
  material experimental archivado.

### Decisiones tomadas

- Mantener una sola ventana Flet y cambiar el contenido entre modos
  `hidden`, `quick` y `full`.
- Mantener el menú contextual del tray y su lifecycle.
- Usar una vista compacta por cards para Quick Panel.
- Mantener compatibilidad con `Individual` y `All lights`, añadiendo selección
  parcial transitoria desde Home sin crear grupos persistentes.
- Usar el sistema i18n existente para todo texto visible.
- Reutilizar Color Studio en vez de construir otro picker o pipeline de color.
- Capturar y restaurar todas las propiedades de ventana alteradas por el modo
  compacto.

### Problemas encontrados y soluciones

- Montar `ColorPanel.main_layout` preservaba la lógica, pero arrastraba peso
  visual de escritorio. Se creó `ColorStudioQuickAdapter`, que compone sólo
  subárboles existentes.
- Los controles Flet no pueden vivir en dos padres activos. El adapter monta
  un único subárbol de Color o White a la vez.
- Los rebuilds por cambio de idioma podían dejar referencias antiguas. El
  adapter remonta los controles reconstruidos.
- El estado externo podía cambiar a White mientras la vista seguía en Color.
  La sincronización remonta el modo correspondiente sin disparar una acción.
- Inicializar un modo White guardado podía enviar Kelvin involuntariamente.
  La composición inicial ahora es pasiva.
- La posición inicialmente se calculaba sólo con el monitor principal. En
  Windows se usa el monitor bajo el cursor del tray, con fallback seguro.

### Decisiones pendientes

- validar visualmente espaciado, foco y jerarquía en la app real;
- validar comportamiento de clic simple, doble clic y menú derecho;
- validar multi-monitor, DPI mixto y posicionamiento;
- validar X11 y AppIndicator/Wayland;
- decidir el criterio de cierre de v1.2 y su integración en una rama de
  release;
- no iniciar una migración general de Flet/Qt sin una decisión separada.

## 5. Quick Panel

### Estado

- **Foundation histórica:** implementada en una rama experimental.
- **Runtime público:** retirado de v1.2.0 por problemas reales de geometría,
  foco y restauración.
- **Próxima decisión:** pausada hasta diseñar una ventana temporal nativa o
  una arquitectura equivalente con lifecycle comprobable.

### Arquitectura y componentes

```text
TrayService
    |
    v
QuickPanelController
    |------------------------------|
    v                              v
QuickPanelView            ActionSequenceExecutor
    |                              |
    v                              v
ColorStudioQuickAdapter       LightController
    |
    v
ColorPanel existente
```

- `core/quick_panel_controller.py`: snapshots, targeting, acciones, modos de
  ventana, geometría, restauración y navegación hacia la Main App.
- `ui/quick_panel_view.py`: shell visual Premium por cards; no descubre
  dispositivos ni ejecuta protocolo.
- `ui/components/quick_color_studio_adapter.py`: frontera de composición
  compacta sobre un `ColorPanel` exclusivo del Quick Panel.
- `core/background/tray_service.py`: traduce intenciones del tray a los
  callbacks del controller.
- `main.py`: compone una `Page`, un `LightController`, un host compartido, la
  Main App y el Quick Panel.

La vista Premium usa cinco secciones: header/dispositivo, power, target, Color
Studio y favoritos. Muestra hasta seis favoritos y permite abrir Favoritos o
Ajustes en la aplicación completa.

### Color Studio adapter

`ColorStudioQuickAdapter` no implementa matemática de color. Monta:

- en modo Color: subárbol Color, controles precisos cuando corresponden,
  brillo y controles de aplicación;
- en modo White: subárbol White, brillo y controles de aplicación.

Preserva picker calibrado, Hue/Purity, HEX/RGB, quick colors, conversión WiZ,
Kelvin real, presets, brightness, throttling, guardas de edición y modo de
aplicación manual. **Color Studio es la fuente de verdad.**

### Comportamiento esperado

- clic primario cuando está oculto: abre o alterna Quick Panel;
- doble clic: abre/restaura la aplicación completa sin flash previo;
- clic derecho: conserva el menú contextual;
- Quick Panel y Main App nunca se muestran simultáneamente;
- modo compacto Windows: `440 x 680`, no redimensionable, siempre encima y a
  16 px de la esquina inferior derecha del área de trabajo;
- al volver a modo full se restauran tamaño, posición, chrome, always-on-top y
  viewport;
- en entornos donde AppIndicator no entrega un clic primario equivalente, el
  menú ofrece acciones explícitas.

### Pendientes manuales

- cerrar cualquier instancia cargada antes del rediseño y arrancar la build
  correcta;
- probar abrir/ocultar, doble clic, menú derecho y restauración;
- probar Color/White, ON/OFF, favoritos y targeting con luces físicas;
- comprobar fidelidad RGB y límites Kelvin;
- comprobar monitor bajo cursor, DPI mixto y varios monitores en Windows;
- comprobar X11 y AppIndicator/Wayland;
- validar foco, frameless y posición real decidida por el compositor.

## 6. Screen Sync / RGBIC

### Investigación externa

- **Repositorio:** `TechAntohere/WizScreenSyncController`
- **URL:** https://github.com/TechAntohere/WizScreenSyncController
- **Autor reportado:** TechAntohere
- **Revisión auditada:** `0feb5749a28389bc6971639467f6cb7fd464ebe2`
- **Auditoría canónica:**
  `docs/third-party/2026-07-26-wizscreensynccontroller-review.md`
- **Permiso:** existe un permiso reportado, pero su alcance y los términos de
  modificación/redistribución siguen pendientes de formalización.
- **Créditos:** pendientes de texto, permiso/licencia y publicación
  definitivos.

El repositorio no contiene una licencia de proyecto. El permiso debe
conservarse como evidencia escrita y aclarar modificación y redistribución
antes de copiar expresión concreta. Hasta entonces, la regla es estricta:
**no copiar código**. Se pueden estudiar comportamientos y **adaptar
conceptos mediante una implementación propia**, con nombres, estructura y
tests propios.

No incorporar la UI PyQt6, su discovery, tray, persistencia ni sockets. El
proyecto externo es un script monolítico; esas responsabilidades ya tienen
dueño en WizZ Desktop.

### Hallazgos técnicos RGBIC

- RGBIC usa `setPilot`.
- Los `sceneId` observados actúan como slots/contenedores, no como
  identificadores fijos. `sceneId: 257` funcionó inicialmente; después de una
  actualización de firmware pareció quedar sobrescrito por un efecto guardado
  del dispositivo, y `sceneId: 258` recuperó el comportamiento esperado.
- `elm` transporta datos dinámicos.
- `elm.steps` contiene steps físicos secuenciales; no representa directamente
  las zonas lógicas de un efecto.
- Se observaron hasta **12 steps** por payload, pero ese límite no implica que
  la tira tenga 12 segmentos ni que el payload cubra toda su longitud.
- `width` es un span físico absoluto: `width: 1` ocupa un segmento físico,
  `width: 2` ocupa dos, y así sucesivamente.
- Los steps se aplican en orden desde el inicio de la tira. Doce steps con
  `width: 1` cubren 12 segmentos; doce con `width: 2` cubren aproximadamente
  24 segmentos.
- El firmware no conoce necesariamente la longitud instalada. Una tira
  cortada puede seguir reportando el mismo modelo.
- La densidad, longitud instalada y calibración determinan la cobertura
  física; no debe existir una tabla fija `modelo -> cantidad de segmentos`.
- `elm.modifier` es global para el programa completo, no por step.
- En las observaciones disponibles, `modifier: 100` corresponde a color
  estático del programa y los valores 101–125 parecen seleccionar efectos
  internos usados por la app WiZ.
- Existen otros rangos con comportamiento de efectos, pero el mapa exacto no
  está completamente documentado. `modifier` debe permanecer como entero
  experimental; no crear enums ni nombres estables todavía.
- Cada step observado contiene 13 enteros; RGB vive en índices 1/2/3,
  `brightness` en índice 7 y `width` absoluto en índice 12. Los demás índices
  observados permanecen en 0 y siguen siendo desconocidos.
- El éxito del transporte no demuestra que el efecto haya sido aplicado. Una
  implementación futura debe representar por separado `transport success` y
  `effect applied`.

Estos hallazgos siguen siendo observaciones que necesitan fixtures, soporte de
capabilities, firmware awareness, probing, fallback acotado de
slots/contenedores y verificación con hardware real. No presentar el formato
como API oficial WiZ ni crear tablas `firmware -> sceneId`.

### RGBIC validation status

- existe un tester comunitario con una tira RGBIC WiZ disponible;
- el dispositivo no es hardware propio del desarrollador;
- existe evidencia física revisada para `ESP25_MHORGB_01` con firmware
  `1.38.0` y una instalación calibrada de 17 segmentos;
- la validación se ejecutó mediante pares de pruebas controladas que
  mantuvieron el payload y cambiaron solamente `sceneId`;
- cada fixture debe registrar modelo, `moduleName`, firmware, payload,
  `elm.steps`, response, resultado de transporte y resultado visual;
- ya existen fixtures sanitizados reales bajo `tests/fixtures/rgbic/`;
- no existe soporte RGBIC productivo ni selección estable de slot;
- existe un encoder puro a params de `setPilot`;
- existe un puente experimental de envío único detrás de `LightController`;
- existe un validador beta local para ejecutar nuevas pruebas controladas sin
  introducir streaming ni soporte productivo.

La metodología y la plantilla documental están en
`docs/codex/queries/2026-07-26-07-rgbic-hardware-validation.md`. La
disponibilidad del tester no autoriza hardcodear un `sceneId`, crear una tabla
por firmware ni asumir que un response exitoso demuestra aplicación visual.

### Screen Sync

La investigación recomienda una fuente pura, independiente de UI y
transporte: captura, análisis de regiones, smoothing, políticas de modo y
backpressure. Screen Sync produciría intención lógica —por ejemplo,
izquierda, centro y derecha— sin elegir spans físicos. Un `PhysicalMapper`
calibrado resolvería después los steps que una sesión realtime controlada por
`LightController` puede emitir.

Reglas:

- `ScreenSyncEngine` no importa sockets, `WizProtocol`, Flet, PyQt6 ni
  PySide6;
- una cola `latest wins` evita acumular frames;
- el scheduler limita Hz y deduplica cambios pequeños;
- fallos de captura se reportan y no envían negro silenciosamente;
- acciones manuales sobre el mismo target deben resolver ownership de forma
  visible y determinista;
- empezar por un MVP Windows de una zona por bombilla;
- Linux/Wayland y RGBIC se validan en fases independientes.

## 7. Effects Engine futuro

La rama actual ya contiene una foundation de modelos y mapping en
`core/effects/`:

- `RGBColor`;
- `EffectFrame`;
- `RGBICFrame` como frame lógico compresible de colores;
- `RGBICStep` como salida física secuencial por step;
- `RGBICProgram` como contenedor físico completo con `modifier` global y
  `support`;
- `CalibrationProfile`;
- `DeviceCapabilities`;
- `compress_rgbic_colors()` para reducir intención lógica a un máximo físico
  seguro cuando una fuente produce más de 12 colores/regiones;
- `map_rgbic_frame()` para distribución uniforme sobre segmentos físicos;
- simulador puro de segmentos físicos secuenciales, con padding negro sólo si
  faltan steps para cubrir toda la calibración.
- encoder puro a params de `setPilot`;
- puente experimental `LightController.send_rgbic_program()` para envío único
  por el camino oficial;
- `tools/rgbic_beta_validator.py` para validación manual y captura de
  artefactos locales sanitizados.

Esos modelos son inmutables e independientes de Flet, sockets y protocolo. La
fase `RGBIC Physical Model Foundation` reemplazó el antiguo scaffolding basado
en `RGBICZone.weight`: el `width` físico absoluto ahora vive únicamente en
`RGBICStep`, mientras `RGBICFrame` conserva la intención lógica sin detalles
de hardware ni WiZ.

La foundation sigue siendo válida por sus frames inmutables, compresión determinista, simulación pura, transporte genérico y desacoplamiento de UDP/UI. Lo incompleto es el camino productivo: calibración persistida, políticas de mapping más ricas, selección/probing de slot, capabilities reales, scheduler, streaming beta y sesión realtime.

El Effects Engine completo sigue siendo trabajo futuro. Debe distinguir:

```text
Logical Effect Zones
    intención del efecto: izquierda, centro, derecha, etc.
    sin LEDs, segmentos ni detalles de WiZ

Physical RGBIC Steps
    color + width absoluto + brightness opcional
    posición determinada por el orden secuencial

RGBIC Program
    steps físicos + modifier global + support experimental

Calibration Profile
    segmentos físicos instalados, tira cortada y densidad/calibración
```

Flujo obligatorio:

```text
Effect Source (Screen Sync, Gradient, Music)
      |
Logical Effect Frame
      |
Physical Mapper  <---------------- Calibration Profile
      |
RGBIC Steps (color + width + brightness)
      |
RGBIC Program (steps + modifier global + support)
      |
LightController
      |
WizProtocol
```

**Regla no negociable:** Effects nunca debe mandar UDP directamente.

### Future RGBIC physical mapping

- `RGBICFrame` expresa la intención lógica actual como una secuencia de
  colores. No conoce segmentos, LEDs, `width`, `modifier` ni WiZ.
- si una fuente lógica produce más de 12 colores/regiones, primero debe pasar
  por una compresión determinista antes del mapping físico; el límite de 12
  pertenece al programa RGBIC físico, no al frame lógico.
- `CalibrationProfile` pertenece a una instalación concreta y hoy describe el
  span físico utilizable mediante `physical_segments`; no se deriva de una
  tabla por modelo.
- `map_rgbic_frame()` es la foundation actual del `PhysicalMapper`: distribuye
  uniformemente `K` colores sobre `N` segmentos con
  `floor((i+1)*N/K) - floor(i*N/K)` y exige que cada step conserve `width > 0`.
- Cada `RGBICStep` físico contiene color, `width` absoluto y `brightness`
  opcional.
- `RGBICProgram` agrega el `modifier` global y `support` experimental
  observados en `elm`.
- El simulador actual expande steps sobre segmentos físicos secuenciales y
  permite validar cobertura, orden y metadata sin `sceneId`, `elm` ni UDP.
- El encoder puro actual recibe `RGBICProgram` y `sceneId`, serializa arrays
  de 13 enteros por step y deja en 0 los índices todavía desconocidos.
- El encoder no decide regiones, calibración, widths ni el significado de
  modifiers.
- El encoder permanece detrás de `LightController`, que sigue siendo el único
  dueño de salida.
- `LightController.send_rgbic_program()` es sólo un puente experimental de
  envío único: distingue transporte de validación visual, exige `sceneId`
  explícito y no implica streaming, scheduler ni soporte estable.
- `tools/rgbic_beta_validator.py` prepara patrones lógicos, comprime si hace
  falta, mapea a steps físicos y guarda artefactos sanitizados para revisión
  humana.

La futura capa debe:

- producir frames lógicos y políticas, no datagramas;
- mantener las zonas lógicas independientes de LEDs y segmentos físicos;
- resolver spans físicos exclusivamente en un `PhysicalMapper` que consuma
  una calibración por instalación;
- representar la salida RGBIC como steps físicos secuenciales con `width`
  absoluto y `brightness` opcional;
- representar `modifier` y `support` como metadata global del programa;
- transportar modifiers experimentales sin convertirlos en un enum ni
  prometer una taxonomía estable;
- usar una sesión realtime con ownership, `latest wins`, rate limiting y
  deduplicación;
- validar capabilities antes de emitir RGBIC;
- incorporar firmware awareness sin decidir sólo por número de versión;
- probar candidatos de slot de forma acotada, aplicar fallback y validar el
  comportamiento observado;
- distinguir éxito de transporte de efecto realmente aplicado;
- dejar el encoder y la serialización WiZ detrás de
  `LightController`/`WizProtocol`;
- permitir que Screen Sync, Gradient y futuros efectos compartan el mismo
  scheduler;
- separar fuente, intención lógica, calibración, mapping, scheduling,
  transporte y UI.

No se debe:

- crear una lookup table fija de cantidad de segmentos por modelo;
- asumir que dos tiras del mismo producto conservan la misma longitud;
- usar el límite de 12 steps como longitud física;
- usar el límite de 12 steps como límite del frame lógico;
- mezclar zonas lógicas con steps RGBIC.
- añadir ahora un enum o catálogo de efectos para `modifier`;
- introducir `width` o `modifier` en el frame lógico.
- hardcodear `sceneId: 257`, 258 u otro slot;
- crear una lookup table `firmware -> sceneId`;
- asumir que un envío exitoso implica que el efecto fue aplicado.

Pendientes concretos:

- diseñar el scheduler y el lifecycle del engine;
- acordar el contrato realtime de `LightController`;
- diseñar el flujo persistido y la UX de calibración por
  dispositivo/instalación;
- ampliar `map_rgbic_frame()` con políticas de mapping distintas de la
  distribución uniforme cuando una fuente futura lo necesite;
- diseñar el encoder de `RGBICStep` a un slot probado y `elm`, con fallback
  acotado y verificación de aplicación;
- capturar fixtures de modifiers y documentar rangos sólo con evidencia;
- detectar capacidades RGBIC reales;
- ejecutar el protocolo documentado de validación comunitaria con payloads
  controlados y rollback seguro;
- añadir Screen Sync y Gradient sólo sobre la infraestructura común.

## 8. `pywizlight`

`pywizlight==0.6.3` es una dependencia runtime requerida y fijada tanto en
`requirements.txt` como en `pyproject.toml`. Actualmente ayuda con discovery y
capacidades a través de `core/pywizlight_adapter.py`, y el pipeline de color
usa sus conversiones desde `core/wiz_color.py`.

La división arquitectónica es:

- UDP nativo WizZ para control frecuente y de baja latencia;
- `pywizlight` para discovery complementario, capacidades, compatibilidad de
  firmware, rangos Kelvin, escenas compatibles y conversión RGBTW;
- nunca llamar `pywizlight` desde sliders, drag de Color Studio, hotkeys,
  tray, rutinas o loops de efectos.

Existe intención de contactar a los desarrolladores de `pywizlight` por
posible soporte RGBIC. **No contactar todavía.** Primero debe existir una
implementación propia reproducible, evidencia de hardware, fixtures de
payload, identificación de capabilities y un caso mínimo que se pueda
explicar o probar upstream.

La actualización a `0.6.5` fue investigada, pero no debe mezclarse con RGBIC ni
con refactors de capacidades. Cualquier upgrade debe ir en un commit aislado,
con diff upstream, tests de adapter, probe físico, build Windows y licencia
exacta empaquetada.

## 9. Decisiones que no deben revertirse fácilmente

1. **No duplicar lógica WiZ.** Discovery, targeting, estado y serialización
   tienen dueños existentes.
2. **No crear controladores paralelos.** Main App, Quick Panel, efectos y
   futuras integraciones usan el mismo `LightController`.
3. **Color Studio es la fuente de verdad** para selección, calibración,
   conversión y comportamiento RGB/White.
4. **Usar capabilities para dispositivos.** No asumir RGB, White, RGBIC o
   Kelvin sólo por la vista activa o por un nombre frágil. La cantidad de
   segmentos físicos instalados pertenece a calibración, no al modelo.
5. **Toda salida WiZ pasa por `LightController` y `WizProtocol`.** Ningún
   Effects Engine, Screen Sync, plugin o UI abre UDP directamente.
6. **`ActionSequenceExecutor` es el motor de acciones discretas.** No
   construir otro executor para tray, hotkeys o Quick Panel; tampoco usarlo
   como streaming de frames.
7. **Mantener una sola ventana y una sola instancia** salvo que una decisión
   arquitectónica futura demuestre otra necesidad.
8. **No bifurcar contratos persistidos por una UI.** Reutilizar managers y
   formatos de config/favoritos.
9. **Usar el i18n existente.** No hardcodear copy visible ni crear un segundo
   mecanismo de traducción.
10. **Documentar colaboraciones externas.** Guardar autor, repositorio,
    revisión, permiso/licencia, ideas adaptadas y créditos.
11. **No copiar WizScreenSyncController.** Adaptar conceptos con
    implementación modular propia.
12. **Cambios a módulos protegidos requieren alcance explícito**, tests y
    justificación antes de editar.
13. **La portabilidad se decide por capacidades efectivas, no sólo por OS.**
    Los adapters futuros implementan contratos compartidos; no crear forks ni
    filtrar APIs nativas hacia el core WiZ.

## 10. Roadmap futuro

### Corto plazo

- ejecutar el plan
  `docs/codex/plans/2026-08-28-v1.3-ui-refactor-and-branch-cleanup.md`;
- limpiar ramas ya integradas y archivar Color Studio legacy/Quick Panel;
- crear `feature/v1.3.0-ui-foundation` desde `main` actualizado;
- consolidar tokens visuales, accesibilidad y controles Flet no deprecados;
- refactorizar primero Home y la selección `single`/`selected`/`all`;
- mantener la beta RGBIC separada de la rama UI pública.

### Mediano plazo

- evaluar Quick Panel sólo después de una decisión separada sobre ventana
  temporal, foco y lifecycle nativo;
- ampliar la matriz Linux beta a otras distribuciones mediante testers;
- mantener macOS diferido hasta disponer de un equipo o tester comunitario;
- diseñar descarga, verificación, instalación y rollback antes de llamar
  “autoactualizador” al cliente de releases;
- diseñar e implementar el Effects Engine común;
- añadir contrato realtime en `LightController`;
- implementar Gradient sobre el scheduler común;
- diseñar calibración y `PhysicalMapper`;
- validar RGBIC con capabilities, calibración y hardware;
- implementar MVP de Screen Sync y después ampliar por plataforma.

### Largo plazo

- integración con Home Assistant;
- soporte de más plataformas;
- arquitectura de plugins;
- más fuentes y efectos sobre el engine común;
- evaluar evoluciones de UI sólo mediante una decisión separada.

## 11. Flujo de trabajo

Siempre:

1. inspeccionar `git status`, rama activa y commits recientes antes de editar;
2. trabajar por ramas de feature/release con alcance claro;
3. usar Codex para implementación y revisión reproducible;
4. clasificar documentación según
   `docs/codex/DOCUMENTATION_GUIDE.md`, usando `queries/` para resultados y
   `plans/` para pasos de ejecución;
5. conservar cambios preexistentes del usuario y no mezclar trabajo ajeno;
6. escribir tests antes o junto con cambios de comportamiento;
7. validar tests focalizados y suite completa en proporción al riesgo;
8. ejecutar `git diff --check` y revisar `git diff`/`git status`;
9. validar manualmente tray, ventana, hardware y build cuando corresponda;
10. documentar cada commit con propósito, archivos, tests, riesgos y
    pendientes;
11. aislar upgrades de dependencias, cambios de protocolo y refactors;
12. no hacer merge, commit o push si la tarea pide esperar revisión.

Un reporte `docs/codex/queries/YYYY-MM-DD-NN-tema.md` debe registrar como
mínimo: rama/base, objetivo, restricciones, decisiones, archivos, validación,
riesgos manuales y próximos pasos. Evidencia externa, permisos y créditos
pertenecen a `docs/third-party/`.

## 12. Problemas conocidos, pendientes y riesgos

### Quick Panel

- falta smoke manual completo de la UI Premium;
- comportamiento de tray y ventana varía entre Windows, X11 y Wayland;
- AppIndicator no siempre expone un clic primario equivalente;
- posicionamiento y foco dependen del compositor;
- multi-monitor con DPI mixto no está validado físicamente;
- la selección parcial transitoria existe en Home, pero Quick Panel todavía
  expone principalmente los modos una/todas;
- el panel actual comparte la ventana principal; la ventana temporal
  independiente está diseñada pero diferida;
- Color/White, favoritos y ON/OFF requieren prueba con hardware real.

### Effects / RGBIC

- la foundation no tiene engine, scheduler ni sesión realtime;
- `LightController.set_rgb()` actual está pensado para acciones, no para
  streaming de vídeo;
- discovery y capabilities productivas aún no reconocen RGBIC;
- la foundation actual ya separa frame lógico, calibración y steps físicos,
  pero el mapper sólo cubre distribución uniforme y no está conectado a
  hardware;
- existe un encoder puro a params de `setPilot`, pero no hay persistencia/
  flujo de calibración ni soporte productivo de streaming;
- existe un puente experimental de envío único y un validador beta manual,
  pero no selección automática de slot ni validación visual automática;
- los slots observados 257/258, `elm.steps`, `width` y `modifier` no están
  documentados como API oficial;
- el slot puede depender del firmware y del estado interno del dispositivo;
- `transport success` no equivale a `effect applied`;
- salvo el comportamiento observado de 100 y el rango aparente 101–125, los
  modifiers globales no tienen semántica estable confirmada;
- no se conoce automáticamente la cantidad de segmentos físicos instalados;
- existen fixtures sanitizados reales y validación revisada para
  `ESP25_MHORGB_01` fw `1.38.0`, pero no validación amplia de payloads en más
  dispositivos o firmwares;
- alta frecuencia puede saturar LAN/dispositivo o disparar demasiadas
  verificaciones de estado.

### Screen Sync

- el permiso/licencia externa debe quedar formalizado antes de copiar código;
- los créditos definitivos siguen pendientes;
- captura de pantalla implica consentimiento, privacidad y permisos;
- HDR, DPI, fullscreen, multi-monitor y hotplug son riesgos;
- Wayland requiere un backend/portal específico;
- no adoptar PyQt6 ni un segundo runtime UI como atajo.

### Cross-platform

- `core/platform/` contiene contratos, fakes y servicios Linux; el runtime
  principal ahora entrega sus servicios a Ajustes, usa XDG para autostart y
  carpetas, y selecciona AppIndicator en GNOME/Wayland antes de iniciar tray;
- `degraded` significa utilizable con limitaciones, no disponibilidad plena;
- el backend productivo de hotkeys para Linux sigue sin decidirse;
- tray, foco, work area y Quick Panel requieren validación X11/Wayland;
- instancia única Unix todavía necesita una decisión de IPC para activación;
- macOS no tiene soporte ni CI activo hasta disponer de validación real;
- Linux sigue siendo beta hasta superar smoke real, build nativa y prueba de
  control LAN en Ubuntu Desktop; no inferir ese estado sólo desde CI o tests.

### Dependencias y arquitectura

- `pywizlight` es requerido aunque algunos comentarios/imports de discovery
  aún toleren su ausencia;
- el límite ideal de imports de `pywizlight` debe seguir vigilándose;
- cualquier upgrade puede cambiar conversión de color o capacidades;
- módulos críticos son grandes y sensibles; evitar refactors no relacionados;
- el estado documentado de tests pertenece a cada commit/reporte y debe
  volver a verificarse después de nuevos cambios.

### Estado de validación conocido

Los resultados concretos de cada fase viven en sus reportes bajo
`docs/codex/queries/`; no se duplican aquí porque dejan de representar el
worktree en cuanto cambia la rama.

Antes de modificar o integrar, ejecutar la validación requerida por la fase y
contrastar siempre rama, commit, `git status` y diff actuales. Las
deprecaciones Flet conocidas pertenecen a la UI existente y deben evaluarse
contra la salida fresca de tests, no contra un conteo histórico.
