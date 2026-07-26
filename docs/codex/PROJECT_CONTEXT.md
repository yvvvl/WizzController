# WizZ Desktop — contexto maestro del proyecto

Última actualización: 2026-07-26

Este documento es la fuente principal de continuidad para nuevas sesiones de
ChatGPT/Codex. Antes de modificar el proyecto, se debe leer completo y
contrastar la rama activa, `git status`, los commits recientes y los reportes
de `docs/codex/queries/`.

## 1. Resumen del proyecto

**WizZ Desktop** es una aplicación de escritorio para controlar luces WiZ
desde Windows mediante la red local. La aplicación principal está construida
con Flet y reúne control de iluminación, Color Studio, escenas, favoritos,
rutinas, hotkeys globales, bandeja del sistema y administración de
dispositivos.

El objetivo es ofrecer un control rápido, privado y fiable que no dependa de
la nube de WiZ para las acciones normales. El camino de control usa UDP LAN
nativo y `setPilot` fire-and-forget; las lecturas, verificaciones de estado y
capacidades permanecen fuera del camino de baja latencia.

El proyecto resuelve varios problemas de la experiencia de escritorio:

- control local aunque Internet no esté disponible;
- acceso rápido desde hotkeys, tray y Quick Panel;
- una única representación de acciones para UI, favoritos y rutinas;
- reproducción de color adaptada a los canales físicos RGBTW de WiZ;
- descubrimiento y selección de dispositivos sin depender de una cuenta
  remota;
- distribución portable para Windows.

La visión futura es convertir WizZ Desktop en una plataforma extensible de
iluminación local: Quick Panel profesional, Effects Engine, RGBIC, Screen
Sync, integración con Home Assistant, más plataformas y plugins. Esa
evolución debe conservar una sola ruta de control y evitar que cada feature
implemente su propio protocolo, discovery o controlador.

## 2. Estado actual

### Versiones y fase de desarrollo

- **Versión estable:** `v1.1.0`, publicada desde `main` y marcada por el tag
  `v1.1.0`.
- **Desarrollo principal declarado:** Quick Panel `v1.2.0`.
- **Estado de Quick Panel:** foundation y rediseño Premium implementados;
  faltan validación manual con ventana/tray reales, hardware y plataformas
  representativas antes de considerarlo terminado para release.
- **Checkout al crear este documento:** rama
  `feature/v1.3.0-effects-engine-foundation`.
- **Foundation experimental adicional:** los modelos base de efectos y RGBIC
  están implementados y pendientes de revisión. Esto no equivale a un Effects
  Engine productivo: no hay scheduler, sesión realtime, Screen Sync, Gradient,
  adaptador RGBIC de hardware ni UI.

### Ramas relevantes

| Rama | Estado y propósito |
| --- | --- |
| `main` | Release estable `v1.1.0` en `0a902d0` |
| `release/v1.1.0` | Preparación de release en `50a4b84` |
| `feature/v1.2.0-quick-panel` | Foundation del Quick Panel; apunta a `1838eca` |
| `feature/v1.2.0-quick-panel-design` | Rediseño Premium terminado en `ec9da58` |
| `feature/v1.3.0-effects-engine-foundation` | Modelos y simulador base de efectos/RGBIC en `0a09163`; pendiente de revisión |
| `feature/v1.1.0-pywizlight-capabilities` | Auditoría, atribución y packaging de `pywizlight` |

La historia de la rama actual pasa por `ea1cc0e` (foundation del Quick Panel),
`ec9da58` (Premium UI) y `0a09163` (foundation de efectos). Existe además el
puntero de rama `feature/v1.2.0-quick-panel` a un commit equivalente de la
foundation (`1838eca`). No asumir que una rama está integrada en `main` sólo
porque su implementación esté completa.

### Últimos commits importantes

| Commit | Importancia |
| --- | --- |
| `0a09163` | `feat: add dynamic effects foundation`; crea modelos inmutables, simulador RGBIC y tests de transporte genérico |
| `ec9da58` | `feat: redesign WizZ Quick Panel UI`; implementa UI Premium, adapter compacto y comportamiento de overlay |
| `ea1cc0e` | `feat: add WizZ Quick Panel foundation`; integra una sola ventana, controller, view y acciones desde tray |
| `0a902d0` | merge de la release `v1.1.0` a `main` y tag estable |
| `50a4b84` | `release: prepare WizZ Desktop v1.1.0` |
| `5948d12` | rediseño de favoritos por capacidades |
| `7ed2923` | inclusión de avisos de terceros para `pywizlight` |

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

### `LightController`

Archivo: `core/light_controller.py`.

Es el controlador central y la única fachada de iluminación que deben usar la
UI y los servicios de aplicación. Sus responsabilidades incluyen:

- ciclo asyncio en un thread dedicado;
- discovery WiZ y caché de dispositivos;
- targeting `single` o `all`;
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

## 4. UI actual

### Estado

- La Main App usa **Flet**.
- Existe una sola `Page` y una sola ventana nativa.
- Main App y Quick Panel comparten el mismo `LightController`.
- La foundation del Quick Panel existe.
- La UI Premium del Quick Panel fue desarrollada.
- La UI completa sigue siendo la fuente para navegación, edición y
  configuración; Quick Panel es una superficie rápida, no un reemplazo.

### Decisiones tomadas

- Mantener una sola ventana Flet y cambiar el contenido entre modos
  `hidden`, `quick` y `full`.
- Mantener el menú contextual del tray y su lifecycle.
- Usar una vista compacta por cards para Quick Panel.
- Mantener `Individual` y `All lights`; grupos parciales están fuera de
  alcance porque exigirían cambiar el contrato de `LightController`.
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

- **Foundation:** implementada.
- **Rediseño Premium:** implementado.
- **Release:** no cerrado; pendiente de revisión y pruebas manuales.

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
- **Permiso recibido/reportado:** el autor autorizó integrar la lógica con los
  créditos correspondientes.
- **Créditos:** pendientes de texto y publicación definitivos.

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
- `sceneId: 257` actúa como contenedor de una escena dinámica.
- `elm` transporta datos dinámicos.
- `elm.steps` contiene las zonas.
- Se observaron hasta **12 zonas**.
- `width`/`weight` representa la distribución o proporción relativa de la
  zona, no un número de LEDs.

Estos hallazgos siguen siendo observaciones que necesitan fixtures, soporte de
capabilities y verificación con hardware real. No presentar el formato como
API oficial WiZ.

### Screen Sync

La investigación recomienda un motor puro, independiente de UI y transporte:
captura, análisis, mapeo de regiones, smoothing, políticas de modo y
backpressure. El engine produciría frames inmutables y los entregaría a una
sesión realtime controlada por `LightController`.

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

La rama actual ya contiene una foundation de modelos en `core/effects/`:

- `RGBColor`;
- `EffectFrame`;
- `RGBICZone`;
- `RGBICFrame`;
- `DeviceCapabilities`;
- simulador puro de 12 zonas con padding negro.

Esos modelos son inmutables e independientes de Flet, sockets y protocolo. El
Effects Engine completo sigue siendo trabajo futuro. La arquitectura deseada
es:

```text
core/effects/
├── modelos: EffectFrame, RGBICFrame y capacidades
├── engine/scheduler común
├── Screen Sync
├── Gradient
└── futuros efectos
```

Flujo obligatorio:

```text
Effects Engine
      |
      v
LightController
      |
      v
WizProtocol
```

**Regla no negociable:** Effects nunca debe mandar UDP directamente.

La futura capa debe:

- producir frames y políticas, no datagramas;
- usar una sesión realtime con ownership, `latest wins`, rate limiting y
  deduplicación;
- validar capabilities antes de emitir RGBIC;
- dejar la serialización WiZ detrás de `LightController`/`WizProtocol`;
- permitir que Screen Sync, Gradient y futuros efectos compartan el mismo
  scheduler;
- separar análisis, scheduling, transporte y UI.

Pendientes concretos:

- diseñar el scheduler y el lifecycle del engine;
- acordar el contrato realtime de `LightController`;
- diseñar el adapter entre `RGBICFrame` y `sceneId`/`elm`;
- detectar capacidades RGBIC reales;
- probar payloads con hardware y rollback seguro;
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
4. **Usar capabilities para dispositivos.** No asumir RGB, White, RGBIC,
   número de zonas o Kelvin sólo por la vista activa o por un nombre frágil.
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

## 10. Roadmap futuro

### Corto plazo

- terminar la validación profesional del Quick Panel;
- realizar smoke manual completo con tray, ventana y luces físicas;
- validar experiencia, foco, espaciado, targeting y multi-monitor;
- revisar la foundation de efectos sin confundirla con una feature terminada;
- decidir cierre e integración de Quick Panel v1.2.

### Mediano plazo

- diseñar e implementar el Effects Engine común;
- añadir contrato realtime en `LightController`;
- implementar Gradient sobre el scheduler común;
- validar RGBIC con capabilities y hardware;
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
4. crear reportes de continuidad en `docs/codex/queries/`;
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
riesgos manuales y próximos pasos.

## 12. Problemas conocidos, pendientes y riesgos

### Quick Panel

- falta smoke manual completo de la UI Premium;
- comportamiento de tray y ventana varía entre Windows, X11 y Wayland;
- AppIndicator no siempre expone un clic primario equivalente;
- posicionamiento y foco dependen del compositor;
- multi-monitor con DPI mixto no está validado físicamente;
- no existen grupos parciales, sólo una luz o todas;
- Color/White, favoritos y ON/OFF requieren prueba con hardware real.

### Effects / RGBIC

- la foundation no tiene engine, scheduler ni sesión realtime;
- `LightController.set_rgb()` actual está pensado para acciones, no para
  streaming de vídeo;
- discovery y capabilities productivas aún no reconocen RGBIC;
- no existe adapter productivo de `RGBICFrame` a `sceneId`/`elm`;
- `sceneId: 257`, `elm.steps` y `weight` no están documentados como API oficial;
- no hay validación de payload con hardware RGBIC real;
- alta frecuencia puede saturar LAN/dispositivo o disparar demasiadas
  verificaciones de estado.

### Screen Sync

- el permiso/licencia externa debe quedar formalizado antes de copiar código;
- los créditos definitivos siguen pendientes;
- captura de pantalla implica consentimiento, privacidad y permisos;
- HDR, DPI, fullscreen, multi-monitor y hotplug son riesgos;
- Wayland requiere un backend/portal específico;
- no adoptar PyQt6 ni un segundo runtime UI como atajo.

### Dependencias y arquitectura

- `pywizlight` es requerido aunque algunos comentarios/imports de discovery
  aún toleren su ausencia;
- el límite ideal de imports de `pywizlight` debe seguir vigilándose;
- cualquier upgrade puede cambiar conversión de color o capacidades;
- módulos críticos son grandes y sensibles; evitar refactors no relacionados;
- el estado documentado de tests pertenece a cada commit/reporte y debe
  volver a verificarse después de nuevos cambios.

### Estado de validación conocido

- Quick Panel Premium: reporte final con `227 passed`, compilación correcta,
  auditoría i18n con 579 claves ES/EN y cero strings sospechosos.
- Foundation de efectos/RGBIC: reporte final con `259 passed`, 32 tests
  focalizados, compilación correcta y auditoría i18n limpia.
- Las 98 advertencias registradas eran deprecaciones Flet preexistentes.

Estos números son evidencia histórica, no sustituyen ejecutar la validación en
la rama que una nueva sesión vaya a modificar.
