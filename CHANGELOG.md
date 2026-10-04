# Changelog

## v1.4.0

### Highlights

- Rebuilt the desktop experience around a native Qt interface for Windows and
  Linux (x64 and ARM64), with Spanish and English UI.
- Redesigned Home, Color Studio, Favorites, Scenes, Routines, Hotkeys, Settings,
  and the multi-light controls for a more consistent, polished workflow.
- Added a movable Quick Panel that snaps to nearby screen edges, remembers its
  position, opens from the tray, and dismisses when it loses focus. On Wayland,
  XWayland is selected when its runtime libraries are available.
- Expanded routines with ordered actions and targets for the current selection,
  all lights, or individual lights/groups.
- Added individual brightness controls, editable quick actions, and complete
  RGB/CCT editors with previews and quick values.
- Improved tray behavior, single-instance activation, close-to-tray handling,
  hotkeys, scrolling, and updater feedback.
- Added checksum-verified updates for installed Linux builds, with staged
  replacement and rollback if the updated app fails to start.
- Published portable Windows and Linux x64/ARM64 packages with SHA-256 checksums.

### Not included

- Screen Sync/Ambilight, audio sync, and RGBIC strip effects remain experimental
  and are not part of this public release.

### Support

WizZ Desktop is an independent project I build as a student. If it is useful to
you, you can support continued development through [GitHub Sponsors](https://github.com/sponsors/yvvvl). Thank you!

### Destacados

- Renovamos la experiencia de escritorio con una interfaz Qt nativa para
  Windows y Linux (x64 y ARM64), disponible en español e inglés.
- Rediseñamos Inicio, Color, Favoritos, Escenas, Rutinas, Atajos, Ajustes y los
  controles para varias ampolletas, con una experiencia más coherente y pulida.
- El panel rápido ahora se puede mover, se ajusta a los bordes cercanos, recuerda
  su posición, se abre desde la bandeja y se oculta al perder el foco. En Wayland
  usa XWayland cuando están disponibles sus bibliotecas.
- Ampliamos las rutinas con acciones ordenadas y objetivos para la selección
  actual, todas las luces o ampolletas/grupos específicos.
- Añadimos controles de brillo individuales, accesos rápidos editables y
  editores RGB/CCT completos con vista previa y valores rápidos.
- Mejoramos la bandeja, la instancia única, cerrar al área de notificación,
  hotkeys, desplazamiento y mensajes del actualizador.
- Incorporamos actualizaciones verificadas por SHA-256 para Linux instalado,
  con reemplazo aislado y restauración si la nueva versión no inicia.
- Incluimos paquetes portables para Windows y Linux x64/ARM64 con sus checksums.

### No incluido

- Screen Sync/Ambilight, sincronización de audio y efectos RGBIC para tiras
  siguen siendo experimentales y no forman parte de esta versión pública.

### Apoyo

WizZ Desktop es un proyecto independiente que desarrollo como estudiante. Si te
resulta útil, puedes apoyar su desarrollo en [GitHub Sponsors](https://github.com/sponsors/yvvvl). ¡Muchas gracias!

## v1.3.5

### Previous release

- Polished Qt transitions, updater feedback, hotkey status, and routine state
  capture; added individual light brightness controls.
- Added checksum-verified updates for installed Linux x64/ARM64 builds with
  staged replacement and rollback.

## v1.3.4

### Fixed

- Prevent the updater from locking the installed application directory while
  replacing it, and restore the previous build if the new executable fails to
  launch.
- Show “Preparing…” while an update downloads and verifies instead of leaving
  the update-check button labeled “Checking…”.

## v1.3.3

### Fixed

- Embed the WizZ light-bulb icon in the Windows executable so desktop
  shortcuts and Explorer no longer show a Python or generic icon.

## v1.3.0

### Added

- Canales de actualización **Estable** y **Beta** persistentes en Ajustes.
- Actualización automática para la distribución portable de Windows: descarga
  el ZIP publicado, comprueba su SHA-256 y reemplaza la app al reiniciarse.
- Publicación de GitHub Releases desde ramas `release/**`, con ZIP y checksum
  adjuntos.

### Notes

- La primera instalación de v1.3.0 sigue siendo manual. Desde esa build,
  las siguientes actualizaciones del canal elegido se aplican desde la app.
- Las builds ejecutadas desde el código fuente no se reemplazan solas: muestran
  la descarga oficial para instalar la primera build portable.
- Las betas cerradas no se publican en GitHub Releases público. Su distribución
  requiere un repositorio privado o un servidor de actualizaciones con accesos
  individuales; un código incrustado en la app no protege una descarga pública.

## v1.2.0

### Added

- Selección temporal de una, varias o todas las ampolletas, sin necesidad de
  crear ni editar grupos persistentes.
- Comprobación manual y segura de actualizaciones desde GitHub Releases.
- Fixture de desarrollo con ampolletas virtuales para validar targeting sin
  necesitar hardware múltiple.
- Beta Linux para Ubuntu Desktop: paquete nativo, persistencia XDG,
  AppIndicator, apertura de Datos/Logs y arranque automático por usuario.
- Instalador Linux sin `sudo`, con lanzador en el menú de aplicaciones y
  desinstalación que conserva los datos personales.

### Changed

- Las builds Windows guardan configuraciones y logs en
  `%LOCALAPPDATA%\\WizZDesktop` y migran datos de instalaciones Flet previas.
- Un clic en el icono de bandeja restaura directamente la ventana principal.
- El Quick Panel experimental fue retirado del flujo público de la bandeja.
- En Linux, los hotkeys globales se muestran como no disponibles: no se usa
  `sudo` ni se intentan hooks inseguros sobre dispositivos de entrada.

### Fixed

- Restauración de ventana, salida real desde la bandeja e instancia única en
  builds Windows.
- Persistencia de datos al reemplazar o ejecutar una copia aislada del
  ejecutable.
- El paquete Linux ahora incluye las dependencias PyGObject/AppIndicator que
  necesita el icono de bandeja fuera del entorno de desarrollo.

### Validation

- 368 pruebas automatizadas completadas en Windows y Ubuntu Desktop; auditoría
  i18n: 608 claves en inglés y español, sin strings UI hardcodeados.
- Validación Windows real: bandeja, hotkeys, instancia única, AppData,
  extracción limpia y control de una ampolleta WiZ por LAN.
- Validación Linux beta real: build nativa, archivo extraído, bandeja,
  persistencia XDG y control LAN de la misma ampolleta WiZ.

> RGBIC, Screen Sync, streaming y actualización automática no forman parte de
> esta versión estable.

## v1.1.0

### Added

- Complete English and Spanish localization.
- Automatic system language detection.
- Manual language selector.
- Redesigned Favorites editor based on device capability:
  - RGB Color Studio editor.
  - White temperature and brightness editor.
  - WiZ scene selector.
  - Brightness-only editor.
- Improved Windows portable distribution.
- Third-party attribution and licensing documentation.

### Fixed

- Favorites editor keeping previous controls after changing type.
- RGB controls appearing in White, Scene and Brightness favorites.
- UI refresh issues after changing favorite modes.
- Windows runtime packaging reliability.

### Technical

- 190 automated tests passing.
- Windows build verified.
- pywizlight license included in distribution.

## 1.0.0 — release candidate

Primera versión de escritorio preparada para distribución en Windows.

### Incluye

- Control local de ampolletas WiZ mediante UDP nativo.
- Color Studio HSV, RGB/HEX, blancos Kelvin, armonías, moods y recientes.
- Escenas, favoritos y rutinas compuestas mediante `ActionSequenceExecutor`.
- Hotkeys globales con backend nativo de Windows y fallback selectivo.
- Bandeja del sistema con acciones rápidas y recuperación de ventana.
- Instancia única con relevo seguro de sesiones desktop zombie.
- UI responsive para Inicio, Color, Escenas, Favoritos, Rutinas, Ajustes y Hotkeys.
- Configuración persistente y logs fuera del directorio de instalación en builds Flet.
- Pipeline reproducible `flet build windows` y artifact de GitHub Actions.

### Eliminado antes de v1

- Reconocimiento y comandos de voz.
- Dependencias `faster-whisper`, `sounddevice` y `numpy` asociadas a voz.

### Validación pendiente para publicar el tag final

- Smoke test del ejecutable en Windows real.
- Inicio con Windows desde el launcher empaquetado.
- Tray, hotkeys e instancia única después de suspensión/reanudación.
- Verificación final del ZIP y checksum generados por el workflow Windows.
