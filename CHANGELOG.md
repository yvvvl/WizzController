# Changelog

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
