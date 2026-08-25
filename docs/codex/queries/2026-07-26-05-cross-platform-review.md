# Cross-platform Foundation review

Status: Investigation

Fecha: 2026-07-26

Rama: `feature/v1.3.0-effects-engine-foundation`

ADR relacionado:

- `docs/adr/0004-cross-platform-architecture.md`

## 1. Objetivo y alcance

Esta revisión pausa Effects Engine para determinar si WizZ Desktop tiene una
base suficiente para evolucionar hacia:

- Windows estable;
- Linux beta;
- macOS experimental.

La respuesta es **sí, con una separación explícita de las integraciones de
escritorio**. El núcleo WiZ no necesita forks ni cambios de protocolo. La
brecha está en hotkeys, tray, autostart, ventanas, instancia única, Quick
Panel y packaging.

Esta fase es exclusivamente documental. No modifica código productivo,
dependencias, UI, workflows ni scripts de build. En particular:

- `LightController` permanece intacto;
- `WizProtocol` permanece intacto;
- no se implementan adaptadores;
- no se crean forks por sistema operativo;
- no se hace commit.

## 2. Método

Se revisaron:

- imports y condiciones de plataforma en `main.py`, `core/`, `config/` y
  `ui/`;
- dependencias de runtime y configuración Flet;
- scripts y workflows de compilación, tests y packaging;
- pruebas existentes de hotkeys, tray, ventanas, instancia única y Quick
  Panel;
- documentación oficial de Flet, pystray, XDG Autostart, Apple
  ServiceManagement y GitHub Actions;
- limitaciones publicadas del paquete `keyboard`.

La clasificación distingue entre lógica portable, implementación
Windows-only y comportamiento que depende de capacidades del escritorio.

## 3. Inventario actual

| Área | Estado actual | Evidencia / límite |
| --- | --- | --- |
| `LightController` | Multiplataforma | Usa Python, `asyncio` y servicios WiZ; no contiene integración de escritorio |
| `WizProtocol` | Multiplataforma | UDP IPv4, `asyncio`, `socket` y `psutil` opcional |
| `pywizlight` adapter | Multiplataforma | Adaptador Python opcional, sin APIs de escritorio |
| Acciones, favoritos, i18n | Multiplataforma | No dependen del OS |
| UI Flet principal | Mayormente multiplataforma | Controles compartidos; semántica de ventana requiere validación nativa |
| Configuración y app storage | Mayormente multiplataforma | Packaged mode usa `FLET_APP_STORAGE_DATA`; algunas preferencias nombran Windows |
| Hotkeys nativas | Windows-only | `WindowsNativeHotkeyBackend` usa `RegisterHotKey` |
| Fallback `keyboard` | Parcial/no apto como contrato | Linux puede requerir acceso privilegiado a dispositivos; OS X es experimental; upstream archivado |
| Tray | Parcial | `pystray` es multi-backend, pero default action, run loop y disponibilidad varían |
| Autostart | Windows-only | Registro HKCU y setting “Start with Windows” |
| Restaurar/focalizar ventana | Windows-only | `core/windows_window.py` usa Win32 |
| Instancia única | Parcial | Windows excluye y activa; Unix sólo hace file lock y no activa la primera instancia |
| Quick Panel: contenido/acciones | Multiplataforma | Reutiliza servicios y `ActionSequenceExecutor` |
| Quick Panel: geometría | Windows-only/parcial | Work area por `user32`; propiedades Flet dependen del window manager |
| Abrir carpeta de datos | Windows-only/parcial | `os.startfile` sólo en Windows; otros sistemas muestran el path |
| Packaging | Windows-only | Sólo hay build y artefacto Windows |
| CI | Headless Linux | Ubuntu ejecuta compile/test; no valida Linux Desktop |

## 4. Hallazgos por área

### 4.1 Núcleo WiZ

La frontera más importante ya existe: `LightController` posee el control de
dispositivos y `WizProtocol` posee el transporte UDP. Ninguno necesita conocer
tray, hotkeys, autostart, ventanas o packaging.

Esto permite compartir el mismo core en las tres plataformas. Los riesgos de
discovery por interfaces, broadcast y firewalls se validan por entorno, pero
no justifican una variante del protocolo por OS.

Decisión:

- conservar ambos módulos sin cambios en Cross-platform Foundation;
- prohibir que futuros adaptadores de escritorio controlen WiZ directamente;
- usar simuladores y tests para el core, y reservar LAN real para smoke tests.

### 4.2 Hotkeys

El backend confiable actual es Windows `RegisterHotKey`. El fallback
`keyboard` no constituye una estrategia estable para Linux/macOS:

- en Linux su acceso global puede depender de `/dev/input` y privilegios;
- su soporte OS X se documenta como experimental;
- el repositorio upstream fue archivado.

La grabación interactiva también depende hoy de `keyboard`, incluso cuando el
registro usa el backend nativo de Windows.

Decisión:

- diseñar un `HotkeyService` con capacidades separadas para registro y
  grabación;
- mantener hotkeys como feature opcional;
- conservar configuraciones aunque el backend no esté disponible;
- no elegir una librería Linux/macOS en esta fase;
- no pedir privilegios elevados como requisito normal de Linux beta.

Fallback:

- mostrar estado y motivo;
- permitir control completo desde UI y menú;
- nunca impedir el arranque.

### 4.3 Tray / menu bar

`pystray` ofrece una base reutilizable, pero no un contrato idéntico:

- Linux puede resolver AppIndicator, GTK o Xorg con capacidades diferentes;
- un tray puede no estar disponible en la sesión de escritorio;
- AppIndicator/macOS no deben depender de una acción predeterminada por click;
- macOS y algunos backends exigen integración correcta con el main thread o
  run loop.

El servicio actual combina un menú portable con restauración y comportamiento
de click específicos de Windows.

Decisión:

- separar definición de menú/acciones del backend nativo;
- usar items explícitos como baseline;
- publicar capacidad de default action;
- si no hay tray, `X` debe cerrar realmente la app;
- deshabilitar “close/start minimized to tray” cuando no exista un tray
  operativo.

### 4.4 Autostart

La implementación actual registra el ejecutable en el Registry de Windows y
fuerza el setting a `false` fuera de Windows. El concepto de producto debe ser
“Start at login”, no “Start with Windows”.

Adaptadores futuros:

- Windows: HKCU Run, preservando el comportamiento actual;
- Linux: entrada `.desktop` bajo XDG Autostart;
- macOS: ServiceManagement dentro del app bundle.

Decisión:

- la preferencia debe ser portable;
- disponibilidad y estado efectivo deben consultarse al adaptador;
- no registrar comandos de desarrollo como si fueran una instalación;
- no ocultar silenciosamente una preferencia sólo por estar en otro OS;
- permisos, identidad del bundle y estado del instalador son parte del
  resultado.

### 4.5 Ventanas e instancia única

Flet expone una API común, pero la restauración/focalización robusta actual es
Win32. En Unix existe exclusión por file lock, pero no un canal para pedir a
la primera instancia que se muestre. Además, el fallback de error del lock
acepta la ejecución para no bloquear desarrollo; esto no es aceptable como
garantía productiva.

Decisión:

- crear contratos futuros `WindowService` y `SingleInstanceService`;
- separar exclusión de activación, porque son capacidades diferentes;
- mantener un fallback Flet para show/hide cuando sea suficiente;
- investigar IPC Unix antes de Linux beta;
- impedir que un fallo desconocido de lock se interprete silenciosamente como
  propiedad de producción.

### 4.6 Quick Panel

La lógica de Quick Panel ya es reusable:

- snapshot de targets, dispositivos, estado y favoritos;
- acciones de encendido, apagado y favoritos;
- cambio entre contenido completo y compacto.

Lo no portable es la promesa visual exacta:

- monitor bajo el cursor y work area;
- esquina inferior derecha;
- foco forzado;
- always-on-top;
- ventana frameless;
- ocultar del taskbar/dock;
- activación desde tray.

Decisión:

- conservar el mismo contenido y acciones;
- consultar capacidades antes de solicitar presentación compacta;
- usar una ventana normal decorada como fallback;
- no prometer geometría Windows en Wayland u otros compositores;
- mantener una acción explícita de menú para abrir el panel;
- nunca crear una ruta alternativa hacia `WizProtocol`.

### 4.7 Packaging

El proyecto configura y automatiza únicamente Windows. Flet permite builds
desktop nativos, pero cada target debe compilarse en su plataforma
correspondiente: Linux en Linux, Windows en Windows y macOS en macOS.

Decisión:

- conservar un verification step compartido;
- crear posteriormente jobs/scripts pequeños por target;
- permitir dependencias por plataforma sin duplicar la aplicación;
- nombrar artefactos por OS y arquitectura;
- diferir formato Linux, signing/notarization macOS y cobertura arm64;
- no publicar Linux/macOS sólo porque un build finalizó.

## 5. Arquitectura propuesta

```text
Main UI / Quick Panel / Settings
                |
      DesktopCapabilities
                |
   Desktop service contracts
      |      |      |      |
   Hotkey  Tray  Autostart Window/Instance
      |      |      |      |
 Windows / Linux / macOS adapters

Shared actions
      |
LightController
      |
WizProtocol
```

Principios:

1. un único composition root elige adaptadores;
2. consumidores consultan capacidades, no nombres de OS;
3. cada servicio tiene una responsabilidad pequeña;
4. features de escritorio se degradan sin degradar el core;
5. adaptadores nunca abren una ruta paralela de control WiZ;
6. tests de contrato usan fakes antes de validar escritorios reales;
7. packaging por target no equivale a fork de producto.

Capacidades mínimas a modelar:

- hotkey register / record;
- tray / default action;
- start at login / permission status;
- show / hide / restore / focus;
- work-area positioning;
- frameless / always-on-top / taskbar skip;
- single-instance exclusion / activation;
- system open-folder.

Una capacidad debe poder expresar `available`, `unavailable`, `degraded` o
`permission_required`, con motivo visible. Un booleano global
`is_cross_platform` no es suficiente.

## 6. Diferencias esperadas por plataforma

### Windows estable

Es el baseline funcional:

- `RegisterHotKey`;
- tray y restauración nativa;
- Registry autostart;
- mutex/eventos para instancia única;
- Quick Panel con work area Win32;
- build y smoke test de artefacto existentes.

La refactorización futura debe proteger este comportamiento con tests antes
de moverlo detrás de contratos.

### Linux beta

Linux no es un único escritorio. La beta debe identificar al menos:

- Ubuntu Desktop GNOME en Wayland;
- Ubuntu Desktop GNOME en X11;
- backend de tray realmente seleccionado;
- disponibilidad de hotkeys sin privilegios;
- semántica de foco y posición;
- entrada XDG Autostart;
- descubrimiento WiZ en una LAN real.

El soporte beta admite degradación documentada. Ubuntu Server y WSL son útiles
para tests/build, pero no sirven como aceptación del escritorio Linux.

### macOS experimental

macOS CI puede probar Python, contratos y producir el bundle. No puede
confirmar:

- interacción humana con menu bar;
- permisos de input/accesibilidad;
- start at login efectivo;
- foco y ciclo de vida de ventanas;
- descubrimiento local WiZ;
- experiencia Gatekeeper/signing/notarization.

Por eso el estado permanece experimental hasta contar con un Mac real o
testers de comunidad. Los resultados deben registrar versión de macOS y
arquitectura.

## 7. Matriz de infraestructura disponible

| Entorno | Uso aprobado |
| --- | --- |
| Windows real | Gate estable completo y hardware WiZ |
| Ubuntu Server | Tests headless, simuladores, contratos y servicios core |
| WSL | Desarrollo, tests y experimento de build Linux |
| Ubuntu Desktop VM | Validación Linux UI, X11/Wayland, tray, ventanas, autostart y package |
| GitHub macOS runner | Compile, tests y build nativo |
| Mac comunitario/real | Smoke de UI, permisos, menu bar, autostart y LAN |

Una VM Linux requiere sesión gráfica real; agregar sólo paquetes GUI a Ubuntu
Server no reemplaza automáticamente la matriz de X11/Wayland.

## 8. Estrategia de pruebas futura

### Nivel 1: portable y simulado

Ejecutable en Windows, Ubuntu Server, WSL y CI:

- contratos de `DesktopCapabilities`;
- selección de adaptadores mediante fakes;
- estados available/unavailable/degraded/permission-required;
- fallback de hotkeys, tray, autostart y Quick Panel;
- menús y acciones sin backend nativo;
- exclusión y activación modeladas por separado;
- invariantes que impidan imports de escritorio desde el core WiZ.

### Nivel 2: adapter contract tests

En el OS nativo:

- registro/desregistro y conflictos de hotkeys;
- ciclo de vida del tray;
- lectura/escritura/desactivación de autostart;
- show/hide/restore/focus;
- lock, segunda instancia y activación;
- detección honesta de capabilities.

Los tests deben limpiar sus registros/archivos y no alterar preferencias
reales fuera de un scope temporal.

### Nivel 3: package smoke

Por artefacto:

- instala o descomprime;
- inicia desde su identidad empaquetada;
- encuentra app storage;
- abre la ventana;
- maneja segunda instancia;
- cierra sin proceso residual;
- conserva metadata/licencias.

### Nivel 4: manual y LAN

- Windows real como release gate;
- Ubuntu Desktop X11 y Wayland para beta;
- Mac real/comunitario para experimental;
- WiZ real en la misma LAN para discovery/control.

CI y simuladores no reemplazan este último nivel, pero permiten diseñar y
validar los contratos antes de disponer de hardware compatible.

## 9. Riesgos y pendientes

Prioridad alta:

1. elegir un backend de hotkeys viable para Linux/macOS sin privilegios
   impropios;
2. decidir IPC de activación de instancia en Unix;
3. integrar correctamente el run loop de tray con Flet;
4. probar Quick Panel bajo Wayland y definir su fallback visible;
5. separar dependencia `keyboard` por plataforma o reemplazarla;
6. crear Ubuntu Desktop VM y macOS CI build.

Pendientes de release:

- formato Linux inicial;
- desktop file, iconos y AppStream/metadata;
- estrategia macOS signing/notarization;
- x64/arm64 por plataforma;
- política de versiones de distribución/macOS;
- proceso de feedback y logs para testers comunitarios.

No se decide una librería concreta, installer, IPC o sistema de signing en
esta revisión.

## 10. Secuencia recomendada

1. aprobar ADR 0004;
2. congelar tests del comportamiento Windows actual;
3. diseñar contratos/fakes y matriz de capabilities;
4. encapsular Win32 sin cambiar comportamiento;
5. implementar fallbacks UI;
6. producir y probar build Linux;
7. implementar adaptadores Linux seleccionados;
8. producir build macOS en CI;
9. distribuir build experimental a testers Mac;
10. reevaluar niveles de soporte antes de volver a ampliar Effects Engine.

Cada punto requiere una fase de implementación separada y revisión previa.

## 11. Fuentes técnicas

- [Flet: publicación y matriz de builds nativos](https://flet.dev/docs/publish/)
- [pystray: uso, main loop y capacidades](https://pystray.readthedocs.io/en/latest/usage.html)
- [pystray: diferencias por plataforma](https://pystray.readthedocs.io/en/latest/faq.html)
- [`keyboard`: plataformas y limitaciones publicadas](https://github.com/boppreh/keyboard)
- [XDG Autostart Specification](https://specifications.freedesktop.org/autostart/0.5/)
- [Apple Service Management](https://developer.apple.com/documentation/servicemanagement/)
- [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

## 12. Resultado

WizZ no necesita una reescritura multiplataforma. Necesita convertir sus
integraciones de escritorio en adaptadores pequeños y capability-driven.

La foundation propuesta mantiene:

- un solo core WiZ;
- un solo modelo de aplicación;
- `LightController` como único dueño de salida;
- `WizProtocol` como transporte;
- Windows como referencia estable;
- Linux/macOS como niveles incrementales, verificables y honestos.

No se modificó código productivo en esta fase.
