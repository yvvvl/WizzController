# Migración gradual a una interfaz nativa Qt Quick

Status: In Progress

Fecha: 2026-08-31

## Objetivo

Reproducir la interfaz Flet aprobada en Qt Quick con controles personalizados,
animaciones fluidas y ventanas desktop reales, manteniendo intacto el núcleo
Python. La migración debe ser reversible hasta la validación final.

## Reglas de trabajo

- La rama estable Flet no se reemplaza ni se elimina durante la POC.
- Cada vista Qt consume el controlador y los servicios existentes mediante un
  bridge pequeño; QML no abre sockets ni persiste JSON.
- Las ampolletas virtuales son la fuente por defecto en desarrollo.
- El frontend general y el experimento RGBIC avanzan en ramas distintas.
- No se migra una vista sin inventariar antes acciones, estados vacíos,
  errores, i18n y comportamiento responsive de su equivalente Flet.
- Las capturas aprobadas y los tokens de `ui/theme.py` son la referencia; no
  se vuelve a reinterpretar el diseño desde cero.

## Fase 0 — corte vertical de viabilidad

- [x] Crear `codex/qtquick-desktop-shell` desde la base UI general.
- [x] Añadir PySide6 como extra opcional `qt-ui`.
- [x] Crear primitives QML para presión, navegación, tarjetas y quick actions.
- [x] Implementar shell frameless con límites de tamaño.
- [x] Implementar Home con selección, power, brillo y acciones rápidas.
- [x] Implementar Quick Panel como segunda ventana nativa.
- [x] Conectar `VirtualLightController` mediante un modelo Qt.
- [x] Probar el bridge y capturar Home/Quick Panel.
- [ ] Medir idle, interacción sostenida y frame pacing.

## Fase 1 — sistema visual común

- [ ] Portar las once paletas actuales y cambio en caliente.
- [ ] Portar reduced motion y duraciones semánticas.
- [ ] Incorporar focus visible, teclado y lectores de pantalla.
- [ ] Sustituir glifos provisionales por el set definitivo de iconos.
- [ ] Añadir sombras/glows con presupuesto de composición controlado.
- [ ] Construir estados hover, press, selected, disabled y loading únicos.
- [ ] Validar 940 × 660, 1120 × 760 y 1280 × 860 sin cortes de scroll.

## Fase 2 — Color Studio

- [ ] Portar el picker RGB continuo como `ShaderEffect` o textura generada en
  GPU, sin reconstruir el árbol QML durante el drag.
- [ ] Actualizar posición, HEX y preview en cada frame visual.
- [ ] Enviar a Python/LAN mediante throttle independiente y último valor gana.
- [ ] Añadir CCT, blancos, brillo, swatches y favorito reactivo.
- [ ] Medir fidelidad al cursor a 60/120/144 Hz.
- [ ] Validar cambio de target durante el drag sin enviar al dispositivo viejo.

## Fase 3 — biblioteca y automatización

- [ ] Favoritos: lista, deduplicación, editor, importación y exportación.
- [ ] Escenas: catálogo, búsqueda, editor guiado y preview.
- [ ] Rutinas: pasos, delays, condiciones, validación y resumen legible.
- [ ] Hotkeys: Windows completo; vista explicativa deshabilitada en Linux.
- [ ] Ajustes: temas, reduced motion, idioma, startup, logs y actualizaciones.

## Fase 4 — integración desktop

- [ ] Reemplazar la gestión de ventana Flet por servicios Qt.
- [ ] Integrar tray e instancia única sin un segundo runtime visual.
- [ ] Conectar Quick Panel a tray/hotkey y ocultarlo al perder foco.
- [ ] Mantener geometría por monitor y work area.
- [ ] Verificar DPI 100/125/150/200 % y múltiples monitores.

## Fase 5 — distribución y decisión

- [ ] Crear builds PySide6 reproducibles para Windows y Linux.
- [ ] Auditar plugins Qt incluidos, licencias, tamaño y firma.
- [ ] Probar actualización y migración sobre una instalación Flet real.
- [ ] Ejecutar beta cerrada separada del experimento RGBIC.
- [ ] Comparar memoria idle, CPU, inicio y tamaño contra Flet.
- [ ] Cambiar el entry point solamente si todas las condiciones del ADR 0007
  están satisfechas.

## Criterios del primer checkpoint

El corte vertical pasa cuando Home y Quick Panel renderizan sin errores QML,
las acciones modifican el controlador virtual inmediatamente, no existe un
segundo `LightController`, las pruebas del bridge pasan y las capturas se
parecen al diseño Flet aprobado. Esta fase no autoriza todavía un release Qt.

