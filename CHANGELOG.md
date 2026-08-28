# Changelog

## v1.2.0

### Added

- Selección temporal de una, varias o todas las ampolletas, sin necesidad de
  crear ni editar grupos persistentes.
- Comprobación manual y segura de actualizaciones desde GitHub Releases.
- Fixture de desarrollo con ampolletas virtuales para validar targeting sin
  necesitar hardware múltiple.

### Changed

- Las builds Windows guardan configuraciones y logs en
  `%LOCALAPPDATA%\\WizZDesktop` y migran datos de instalaciones Flet previas.
- Un clic en el icono de bandeja restaura directamente la ventana principal.
- El Quick Panel experimental fue retirado del flujo público de la bandeja.

### Fixed

- Restauración de ventana, salida real desde la bandeja e instancia única en
  builds Windows.
- Persistencia de datos al reemplazar o ejecutar una copia aislada del
  ejecutable.

### Validation

- 361 pruebas automatizadas completadas durante la preparación del release.
- Validación Windows real: bandeja, hotkeys, instancia única, AppData,
  extracción limpia y control de una ampolleta WiZ por LAN.

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
