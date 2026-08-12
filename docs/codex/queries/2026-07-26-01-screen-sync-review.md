# Screen Sync architecture review

Status: Investigation

- **Proyecto:** WizZ Desktop
- **Fecha:** 2026-07-26
- **Fase:** evaluación arquitectónica
- **Repositorio externo:** https://github.com/TechAntohere/WizScreenSyncController
- **Revisión externa auditada:** `0feb5749a28389bc6971639467f6cb7fd464ebe2`
- **Alcance:** análisis y documentación; sin código productivo, dependencias,
  cambios de UI ni commit

## 1. Resumen ejecutivo

WizScreenSyncController demuestra que la captura de pantalla, el promedio por
regiones normalizadas, el suavizado temporal y un payload WiZ RGBIC de hasta
12 steps son técnicamente viables. No es, sin embargo, un módulo integrable:
es un script PyQt6 monolítico de 1.796 líneas que también descubre dispositivos,
persiste configuración, crea la bandeja y envía UDP directamente.

La recomendación es **adaptar los conceptos, no integrar el programa**. WizZ
debe construir un motor propio, independiente de UI y transporte, que publique
frames de iluminación a un contrato de streaming de `LightController`.
`ScreenSyncEngine` nunca debe importar sockets, `WizProtocol`, Flet, PyQt6 ni
PySide6.

Hay dos gates antes de implementar:

1. **legal:** el repositorio externo no tiene licencia y el permiso comunicado
   necesita quedar archivado con derechos de modificación y redistribución;
2. **técnico:** el `LightController.set_rgb()` actual no es un sink de vídeo;
   cada envío programado dispara verificaciones posteriores y callbacks, por
   lo que se necesita un contrato de streaming coalescido dentro del
   controlador.

Recomendación final: **adaptar**, comenzando por un MVP Windows de una zona por
bombilla. Linux/Wayland y el mapping RGBIC calibrado deben permanecer como
fases posteriores con pruebas de plataforma y hardware real.

## 2. Repositorio externo

### 2.1 Estructura

```text
WizScreenSyncController/
├── README.md
├── requirements.txt
└── wizscreensynccontroller.py
```

No se encontraron:

- tests;
- CI;
- `LICENSE` o `COPYING`;
- configuración de packaging;
- modelos o interfaces estables;
- módulos separados para captura, análisis o transporte.

La rama auditada tenía 16 commits. El commit más reciente era del 7 de febrero
de 2026. Fuentes:

- [repositorio](https://github.com/TechAntohere/WizScreenSyncController);
- [script principal](https://github.com/TechAntohere/WizScreenSyncController/blob/0feb5749a28389bc6971639467f6cb7fd464ebe2/wizscreensynccontroller.py);
- [requirements](https://github.com/TechAntohere/WizScreenSyncController/blob/0feb5749a28389bc6971639467f6cb7fd464ebe2/requirements.txt);
- [commit auditado](https://github.com/TechAntohere/WizScreenSyncController/commit/0feb5749a28389bc6971639467f6cb7fd464ebe2).

### 2.2 Componentes encontrados

| Componente | Responsabilidad real | Observación |
| --- | --- | --- |
| `DiscoveryWorker` | broadcast UDP `getSystemConfig` | Duplica el discovery de WizZ |
| `MultiSyncWorker` | captura, análisis, smoothing y UDP | Mezcla cuatro responsabilidades críticas |
| `CanvasZone` | región visual normalizada por dispositivo/zona | La idea de coordenadas normalizadas es reutilizable |
| `WiZApp` | UI, configuración, escenas, lifecycle y tray | No debe incorporarse |
| `_send_to_device` / `_udp` | serialización `setPilot` y socket | Viola la frontera requerida |

### 2.3 Flujo de datos observado

```text
DXcam opcional o MSS
        │
        ▼
array BGR/BGRA de NumPy
        │
        ▼
submuestreo por stride
        │
        ▼
regiones normalizadas por dispositivo y zona
        │
        ▼
promedio + filtro de highlights + subtitle guard
        │
        ▼
gamma/saturación/ganancia/brillo + smoothing
        │
        ▼
JSON setPilot
        │
        ▼
socket UDP directo :38899
```

Para bombillas se envía el primer color. Para tiras se construye una escena
dinámica `sceneId: 257` con 12 pasos RGBIC. El loop admite un objetivo de 10 a
60 FPS y envía un paquete por dispositivo y frame.

Ese 257 describe la revisión externa auditada, no un contrato estable de WiZ.
Información posterior de TechAntohere mostró que 257 podía quedar ocupado
después de una actualización de firmware y que 258 recuperaba el efecto. WizZ
no debe copiar ni hardcodear ninguno de esos slots.

### 2.4 Fortalezas técnicas

- regiones expresadas como fracciones del frame, independientes de resolución;
- downsampling barato antes del análisis;
- cálculo vectorizado con NumPy;
- smoothing por dispositivo;
- ganancias RGB, saturación, brillo y umbral oscuro configurables;
- fallback de DXcam a MSS;
- preview y métricas de FPS/tiempo de proceso;
- soporte conceptual para bombilla y tira segmentada.

### 2.5 Debilidades técnicas

- todas las capas están acopladas a `QThread` y PyQt6;
- captura, procesamiento y salida comparten un único loop;
- no existe backpressure: no se define qué frame descartar si una etapa se
  retrasa;
- abundan excepciones silenciadas, por lo que una captura o un envío pueden
  fallar sin diagnóstico;
- el worker se inicia antes de cargar configuración;
- DXcam crea la cámara una vez con el monitor inicial; cambiar el monitor no la
  recrea;
- UI y worker comparten listas y mapas mutables sin snapshot ni lock;
- el proceso no implementa cierre explícito y verificable del worker/socket;
- `gamma` y `adaptive_brightness` se declaran pero no se usan;
- `dxcam` se importa como optimización, pero no está declarado en
  `requirements.txt`;
- las dependencias no tienen pins;
- la métrica `latency` sólo mide tiempo local del loop, no antigüedad del frame,
  red ni reacción visible de la luz;
- cada frame envía UDP aunque el color no haya cambiado de forma perceptible;
- no hay tests de fórmulas, límites de ROI, canales, smoothing o payload RGBIC.

El ajuste `use_perceptual` no debe trasladarse literalmente. Convierte sRGB a
una aproximación lineal antes de enviar. `LightController.set_rgb()` ya espera
un color lógico de pantalla y lo convierte a canales físicos WiZ; reutilizar
ambas transformaciones produciría doble corrección y colores más oscuros.

## 3. Arquitectura actual de WizZ relevante

WizZ ya separa intención, control y protocolo:

```text
UI / Tray / Hotkeys / Favorites / Routines
                    │
                    ▼
         ActionSequenceExecutor
                    │
                    ▼
             LightController
                    │
                    ▼
             WizProtocol / UDP
```

Hallazgos concretos:

- `LightController` posee targeting, discovery, estado, conversión RGBTW,
  coalescing y UDP;
- el hot path normal usa `set_rgb()` y un pump con intervalo configurable de
  35 a 200 ms, 65 ms por defecto;
- cada paquete emitido agenda dos lecturas `getPilot` posteriores y puede
  notificar UI/tray;
- `ActionSequenceExecutor` serializa acciones discretas y permite esperas; no
  es adecuado para un stream de frames;
- `QuickPanelController`, Flet y `TrayService` ya consumen el mismo
  `LightController`;
- la distribución actual es Windows, aunque CI ejecuta tests en Ubuntu y la
  arquitectura contempla comportamiento Linux futuro.

Conclusión: Screen Sync debe compartir el controlador existente, pero no debe
llamar `set_rgb()` ingenuamente a 30 o 60 FPS ni pasar cada frame por
`ActionSequenceExecutor`.

## 4. Dependencias

El proyecto externo declara, sin versiones:

```text
PyQt6
mss
numpy
```

Además intenta importar `dxcam`, que no está declarado.

Las cifras siguientes son tamaños de descarga de wheels publicados al
2026-07-26, no el tamaño instalado ni el impacto final de la build.

| Paquete | Peso de referencia Windows x64 | Plataformas/licencia | Decisión |
| --- | ---: | --- | --- |
| PyQt6 6.11 | ~6,8 MB más ~78,4 MB de Qt6 | Windows/Linux/macOS; GPLv3 o comercial | Rechazar para Screen Sync |
| MSS 10.2 | ~67 kB | Windows/macOS/X11; MIT | Evaluar como fallback |
| NumPy 2.5.1 | ~12,4 MB | Multiplataforma; BSD y avisos asociados | Probable, con pin compatible |
| DXcam 0.3 | ~339 kB, sin contar transitivas | Sólo Windows; MIT | Evaluar como backend opcional |
| PySide6 6.11 | meta + Essentials/Addons muy grandes | Windows/Linux/macOS; LGPL/GPL/comercial | No añadir sólo por Screen Sync |

Fuentes:

- [PyQt6 y licencia](https://www.riverbankcomputing.com/software/pyqt);
- [runtime Qt6 de PyQt6](https://pypi.org/project/PyQt6-Qt6/);
- [MSS](https://pypi.org/project/mss/);
- [NumPy](https://pypi.org/project/numpy/);
- [DXcam](https://pypi.org/project/dxcam/);
- [PySide6](https://pypi.org/project/PySide6/).

### Conflictos y decisiones

1. **PyQt6:** añade una segunda UI, un runtime Qt grande y obligaciones GPL o
   comerciales. No es necesario para el motor y no debe añadirse.
2. **NumPy:** la versión 2.5.1 requiere Python 3.12+, mientras WizZ declara
   Python 3.11–3.13. Debe fijarse una versión compatible con todo el rango o
   aprobarse un aumento del mínimo de Python.
3. **MSS:** es pequeño y no tiene dependencias Python, pero su backend Linux
   10.2 es explícitamente X11. No resuelve Wayland nativo.
4. **DXcam:** ofrece captura Windows de baja latencia con DXGI/WGC, pero debe
   ser una dependencia opcional declarada, con fallback y pruebas de packaging.
5. **PySide6:** su valor sólo aparece si WizZ adopta Qt de manera más amplia.
   `QScreenCapture` pertenece a Qt Multimedia y arrastra Addons; no debe
   introducirse como atajo de captura dentro de una app Flet.

## 5. Licencia y créditos

No hay licencia detectable en el repositorio externo. Bajo las reglas por
defecto no debe copiarse, modificarse ni redistribuirse el script sólo porque
sea público:

https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

El brief indica un permiso del autor condicionado a créditos. Antes de usar
expresión concreta del código se debe conservar ese mensaje y aclarar alcance,
redistribución, duración, revisiones cubiertas y titularidad.

La evaluación detallada y el borrador no publicable de
`THIRD_PARTY_NOTICES.md` están en:

`docs/third-party/2026-07-26-wizscreensynccontroller-review.md`

No se modificó ningún archivo de créditos definitivo.

## 6. Compatibilidad de plataforma

### 6.1 Windows

**Captura**

- MSS usa APIs de captura de Windows y es un fallback simple.
- DXcam usa Desktop Duplication API y ofrece una ruta más apropiada para alta
  frecuencia y juegos Direct3D.
- El código externo elige DXcam si el import funciona; no permite elegir
  backend ni recuperarse de todos los fallos durante ejecución.

**Rendimiento y latencia**

- downsampling por stride y NumPy reducen el costo del análisis;
- una captura completa sigue copiando el frame antes de submuestrearlo;
- el promedio por ROI se repite por dispositivo, aunque varios dispositivos
  compartan regiones;
- 60 FPS de captura no implica 60 actualizaciones útiles de una luz WiZ;
- hay que medir por separado edad del frame, análisis, cola de salida, red y
  reacción física.

**Múltiples monitores**

- MSS enumera monitores y el script usa índices;
- los índices pueden cambiar tras desconectar, reordenar o reanudar pantallas;
- el backend DXcam queda ligado al monitor usado al crear la cámara;
- faltan pruebas con DPI mixto, escalado, rotación, HDR y varios adaptadores.

**Conclusión Windows:** viable para un MVP, empezando a 10–20 Hz de salida y
subiendo sólo con medidas y hardware real.

### 6.2 Linux X11

MSS 10.2 implementa backends GNU/Linux X11 mediante XCB/XShm/XGetImage y un
fallback Xlib. Requiere `DISPLAY` y librerías del sistema. La captura debería
funcionar en escritorios X11 compatibles, pero el proyecto externo no aporta
tests ni packaging Linux.

Fuente del backend:

https://github.com/BoboTiG/python-mss/blob/v10.2.0/src/mss/linux/__init__.py

**Conclusión X11:** técnicamente plausible, no validado.

### 6.3 Linux Wayland y PipeWire

El proyecto externo no contiene integración con:

- XDG Desktop Portal ScreenCast;
- PipeWire;
- selector de pantalla del compositor;
- tokens de sesión ni permisos;
- recuperación tras revocación o cambio de monitor.

MSS no ofrece aquí una ruta Wayland nativa. XWayland no debe asumirse capaz de
capturar todo el escritorio. Qt documenta que en Wayland `QScreenCapture`
requiere ScreenCast Portal y PipeWire 0.3, y que la selección la controla un
wizard del sistema:

https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QScreenCapture.html

**Conclusión Wayland:** no compatible con la implementación externa; requiere
un backend específico y permisos explícitos. Debe quedar experimental hasta
probar GNOME, KDE y al menos una distribución representativa.

### 6.4 Limitaciones visuales

- HDR y espacios de color amplios pueden producir colores lavados o clipping;
- el orden BGRA/BGR/RGB debe formar parte del contrato de captura;
- DPI y escala lógica no deben usarse para indexar buffers físicos;
- subtítulos, flashes y letterboxing necesitan políticas distintas por modo;
- nunca deben persistirse frames ni píxeles en logs.

## 7. Reutilización y alternativas

### 7.1 Matriz de decisión por componente

| Parte externa | Tratamiento | Motivo |
| --- | --- | --- |
| Concepto de layout normalizado | Adaptar con implementación propia | Es independiente de resolución y sirve para multi-monitor |
| Downsampling y promedio de ROI | Reescribir y probar | La estrategia es útil; la expresión concreta y sus edge cases no |
| Smoothing, ganancias y saturación | Adaptar | Deben convertirse en `ModePolicy` y respetar el pipeline RGBTW de WizZ |
| Filtro de highlights/subtítulos | Adaptar sólo para Cinema | Es heurístico y necesita fixtures antes de aceptarse |
| Selección DXcam/MSS | Adaptar como factory de backends | El fallback es útil, pero requiere pins, diagnóstico y lifecycle |
| Payload RGBIC de hasta 12 steps | Investigar; no reutilizar aún | `width` físico, calibración y constantes no documentadas, sin capability ni hardware tests |
| `MultiSyncWorker` | Reescribir por completo | Acopla captura, análisis, estado, Qt y UDP |
| `DiscoveryWorker` | Rechazar | `LightController` ya posee discovery y targeting |
| `_udp` y `_send_to_device` | Rechazar | Screen Sync no puede controlar sockets |
| UI, tray, escenas y JSON | Rechazar | Duplican Flet, `TrayService` y managers de `config/` |
| Clases/widgets PyQt6 | Rechazar | Segunda UI, licencia GPL/comercial y runtime duplicado |

“Adaptar” significa reproducir el comportamiento deseado mediante interfaces y
tests propios, no trasladar funciones del script mientras la licencia siga sin
resolver.

### 7.2 A. Copiar y dividir el monolito

**Ventaja:** llegada aparentemente rápida a paridad.

**Desventajas:** licencia sin resolver, PyQt6, UDP duplicado, configuración
duplicada, deuda de threading y ausencia de tests.

**Decisión:** rechazar.

### 7.3 B. Motor modular en el mismo proceso

Crear un paquete Python puro con backends de captura intercambiables y un
puerto de salida implementado por `LightController`.

**Ventajas:** sigue la arquitectura actual, facilita tests, evita IPC y permite
reusar targeting/capabilities/protocolo.

**Desventajas:** captura y análisis comparten proceso con UI; un backend nativo
defectuoso puede afectar estabilidad.

**Decisión:** recomendada para el MVP.

### 7.4 C. Captura/análisis en sidecar, salida en WizZ

El sidecar captura y analiza, pero envía `LightFrame` por IPC al proceso
principal. Sólo `LightController` habla WiZ.

**Ventajas:** aislamiento de crashes, permisos y runtimes de captura; apto para
Qt/Wayland futuro.

**Desventajas:** protocolo IPC, supervisión, packaging y sincronización de
configuración agregan complejidad.

**Decisión:** reservar si las pruebas muestran inestabilidad o si Qt se adopta
sin migrar todavía la UI principal.

## 8. Arquitectura propuesta

### 8.1 Estructura lógica futura

```text
core/
└── screen_sync/
    ├── models.py
    ├── capture.py
    ├── analyzer.py
    ├── mapper.py
    ├── modes.py
    ├── output.py
    └── engine.py
```

Si los backends crecen, `capture.py` puede evolucionar a:

```text
core/screen_sync/capture/
├── base.py
├── windows_dxcam.py
├── mss_x11.py
└── wayland_pipewire.py
```

Responsabilidades:

| Unidad | Responsabilidad | No debe conocer |
| --- | --- | --- |
| `models.py` | frames, regiones, colores, config y estados inmutables | UI, sockets |
| `capture.py` | enumerar fuentes y producir el frame más reciente | WiZ, modos |
| `mapper.py` | convertir layout normalizado en ROIs válidas | captura nativa, UDP |
| `analyzer.py` | extraer colores y estadísticas de píxeles | dispositivos, UI |
| `modes.py` | smoothing, saturación y política temporal | captura, protocolo |
| `output.py` | adaptar `LightFrame` al contrato de `LightController` | sockets |
| `engine.py` | lifecycle, pipeline, backpressure y métricas | detalles de UI/protocolo |

### 8.2 Flujo obligatorio

```text
CaptureBackend
      │ PixelFrame
      ▼
ZoneMapper
      │ regiones
      ▼
ColorAnalyzer
      │ colores medidos
      ▼
ModePolicy
      │ LightFrame
      ▼
LightController realtime session
      │
      ▼
WizProtocol / UDP
```

Dependencias prohibidas:

```text
ScreenSyncEngine ─X─> socket
ScreenSyncEngine ─X─> WizProtocol
ScreenSyncEngine ─X─> PyQt6/PySide6/Flet
CaptureBackend   ─X─> LightController
```

### 8.3 Contrato de salida necesario

El API público actual de `LightController` sirve para acciones discretas. En
una fase aprobada deberá añadirse un concepto de **sesión realtime** dentro
del propio controlador:

```text
acquire_realtime_session(source, target_ids, max_hz) -> handle
submit_realtime_frame(handle, colors_by_target) -> result
release_realtime_session(handle, restore_previous_state) -> None
```

No es una firma final; define las responsabilidades mínimas:

- ownership explícito de targets;
- una única cola `latest wins`;
- rate limit por dispositivo;
- deduplicación por delta de color;
- coalescing dentro de `LightController`;
- health check periódico, no dos `getPilot` por frame;
- callbacks de UI limitados a métricas, no a cada color;
- serialización de bombilla o RGBIC en la capa WiZ existente;
- restauración controlada al detener;
- una acción manual sobre el mismo target detiene o reemplaza la sesión de
  forma visible y determinista.

`ActionSequenceExecutor` puede iniciar/detener un preset de Screen Sync, pero
no debe transportar frames.

### 8.4 Concurrencia y backpressure

- un worker de captura produce como máximo un frame pendiente;
- si llega otro frame, reemplaza al anterior;
- analyzer y output consumen snapshots inmutables;
- el scheduler de salida limita Hz independientemente de FPS de captura;
- los colores por debajo de un delta configurable no generan UDP;
- un fallo de captura conserva el último estado, muestra error y detiene la
  sesión tras un umbral; no envía negro silenciosamente;
- stop espera cierre de backend, libera recursos y después restaura o conserva
  el estado según configuración;
- todas las excepciones llegan a un estado tipado y a logs sin datos de imagen.

### 8.5 Modos

| Modo | Análisis/política | Frecuencia inicial sugerida |
| --- | --- | ---: |
| Ambient | promedio estable, saturación neutra, smoothing medio | 8–12 Hz |
| Gaming | smoothing bajo, delta pequeño, saturación opcional | 15–20 Hz |
| Cinema | smoothing alto, protección de subtítulos/letterbox y highlights | 10–15 Hz |
| Music | fuente de audio futura que reutiliza `ModePolicy` y output | fuera de alcance |

Las frecuencias son puntos de partida para pruebas, no promesas. Captura puede
funcionar a más FPS que la salida WiZ.

### 8.6 Bombillas y RGBIC

**MVP:** una región y un RGB por bombilla usando targeting/capabilities de WizZ.

**RGBIC futuro:** `LightFrame` puede contener varias zonas lógicas. Un mapper
calibrado debe convertirlas en steps físicos secuenciales antes de que
`LightController` valide capability y coordine el encoding del payload. La
escena dinámica externa usa constantes y un formato no cubierto por el API
actual; debe investigarse, probarse con fixtures y verificarse en hardware
antes de incorporarlo.

Fallback recomendado: si un dispositivo no soporta segmentos, combinar sus
zonas a un único color promedio.

## 9. Relación con PySide6/Qt

Una futura UI Qt sí puede beneficiar la experiencia de Screen Sync:

- overlay nativo para dibujar y mover regiones;
- modelos de pantallas y ventanas;
- señales, threads y lifecycle de escritorio coherentes;
- tray y atajos integrados;
- `QScreenCapture`/`QWindowCapture`;
- portal de selección Wayland gestionado por Qt.

No garantiza más rendimiento. `QScreenCapture` usa Qt Multimedia, tiene
limitaciones Wayland y un footprint considerable. Tampoco conviene ejecutar
dos frameworks de UI con event loops propios en el mismo proceso sin un diseño
explícito.

Decisión:

- mantener el engine y sus tests totalmente independientes de Qt;
- no portar la UI externa PyQt6;
- no añadir PySide6 en esta fase;
- si se aprueba una migración general del Quick Panel, implementar sólo un
  adapter Qt que consuma el mismo engine;
- si Flet y Qt deben coexistir temporalmente, preferir un sidecar Qt antes que
  dos loops de UI en el proceso principal.

## 10. Riesgos

| Riesgo | Nivel | Mitigación |
| --- | --- | --- |
| Ausencia de licencia externa | Alto/bloqueante | permiso escrito o licencia antes de copiar |
| Saturar WiZ/LAN con frames | Alto | rate limit, latest-wins, deduplicación y hardware tests |
| Sobrecargar verificaciones de `LightController` | Alto | sesión realtime con health checks periódicos |
| Payload RGBIC no documentado/validado | Alto | fase separada, capability y fixtures físicos |
| Wayland sin portal/PipeWire | Alto | backend específico y matriz GNOME/KDE |
| Captura sensible | Alto | consentimiento, indicador, memoria efímera, cero píxeles en logs |
| HDR/DPI/multi-monitor | Medio-alto | IDs estables, normalización física y matriz manual |
| PyQt6/GPL y runtime duplicado | Alto | no adoptar PyQt6 |
| Dependencias sin pin | Medio-alto | pins, hashes, notices y build reproducible |
| Conflictos UI/manual vs sync | Medio | ownership visible y regla determinista |
| Consumo CPU/latencia | Medio | benchmark por etapa, downsample y frame dropping |

## 11. Cambios futuros necesarios en WizZ

Ninguno se implementa en esta fase. Una aprobación posterior implicaría:

1. formalizar el permiso/licencia y créditos;
2. definir modelos e interfaces de Screen Sync;
3. añadir un contrato realtime a `LightController` sin exponer UDP;
4. separar verificación normal de health checks de streaming;
5. implementar captura Windows tras benchmark MSS vs DXcam;
6. implementar analyzer/mapper/modes con frames sintéticos;
7. crear persistencia atómica mediante un manager de `config/`;
8. integrar controles Flet sólo después de estabilizar el engine;
9. añadir backend X11 y luego Wayland/PipeWire como fases independientes;
10. investigar RGBIC sólo con hardware y rollback seguro;
11. actualizar requirements, build, licencias y notices en commits aislados.

El core existente no necesita ser reemplazado. Requiere una extensión
acotada y explícita para streaming.

## 12. Estrategia de pruebas y aceptación

### Automatizadas

- analyzer con arrays sintéticos de color sólido, bordes, barras negras,
  highlights y subtítulos;
- mapper con ROIs vacías, fuera de rango, solapadas y distintos DPI/aspectos;
- modes con reloj falso y secuencias deterministas;
- engine con backend y output falsos, incluyendo drop de frames y errores;
- output con protocolo falso: rate limit, latest-wins, delta y lifecycle;
- regresión que impida imports de sockets/protocolo desde `core.screen_sync`;
- compatibilidad Python 3.11–3.13 o rango que se apruebe;
- tests de payload RGBIC separados de los de análisis.

### Manuales

- Windows 10/11, uno y varios monitores, DPI mixto, HDR on/off;
- escritorio, vídeo, juego borderless y fullscreen;
- una y varias luces, Wi-Fi cargado y dispositivo offline;
- suspensión/reanudación, hotplug y cambio de monitor;
- X11 representativo;
- Wayland GNOME/KDE con permisos concedidos, denegados y revocados;
- build portable con notices y sin dependencias accidentales.

### Métricas a registrar

- FPS capturados, procesados y enviados por separado;
- edad p50/p95 del frame al enviarlo;
- CPU y memoria;
- frames descartados;
- datagramas por segundo y target;
- errores/reintentos;
- reacción visible medida con hardware, no sólo tiempo del loop.

## 13. Estimación de complejidad

Estimación orientativa para una persona con acceso a hardware WiZ:

| Alcance | Complejidad | Esfuerzo aproximado |
| --- | --- | ---: |
| Gate legal y ADR/API final | Media | 2–4 días |
| Engine puro + analyzer/mapper/modes | Media-alta | 1–2 semanas |
| Sesión realtime en `LightController` | Alta | 1 semana |
| MVP Windows, bombilla, Ambient/Cinema | Alta | 1–2 semanas |
| UI, configuración y packaging Windows | Media-alta | 1 semana |
| X11 validado | Media | 3–5 días |
| Wayland Portal/PipeWire | Alta | 1–2 semanas |
| Mapping y payload RGBIC calibrados | Alta | 1–2 semanas |

Un MVP Windows para bombillas está en el orden de **3–5 semanas**. El alcance
multiplataforma con Wayland y RGBIC está en el orden de **6–10 semanas**,
dependiendo del hardware, permisos, packaging y resultados de benchmarks.

## 14. Recomendación final

### Decisión: adaptar

No integrar el script externo ni sus capas PyQt6/UDP. Conservar la atribución y
reimplementar de forma modular las ideas útiles:

- layouts normalizados;
- downsampling;
- análisis por ROI;
- smoothing y calibración;
- backend Windows rápido con fallback;
- salida de una o varias zonas.

Orden recomendado tras aprobación:

1. resolver permiso/licencia;
2. acordar el contrato realtime de `LightController`;
3. construir engine puro con fakes y benchmarks;
4. entregar MVP Windows de una zona;
5. evaluar UI;
6. abordar X11, Wayland y RGBIC en gates separados.

La arquitectura objetivo queda:

```text
Core Python
├── Main UI
├── Quick Panel
└── Screen Sync Engine
          │
          ▼
   LightController
          │
          ▼
      WizProtocol
```

Screen Sync no conoce ni envía UDP.
