# Phase55 — Rutinas visuales

Enfoque: mejorar la vista de Rutinas para que deje de usar `tipo + valor` técnico.

Cambios:
- Reemplaza `ui/components/routines_panel.py`.
- Agrega/actualiza `ui/scene_visuals.py` con iconos locales de escenas.
- Actualiza `core/action_sequence.py` para permitir acción `routine` sin deadlock.
- Agrega `pytest.ini` para que los tests encuentren `core/` y `config/`.

No toca:
- Voz.
- LightController/WiZ.
- Bandeja/tray.
- main.py.
- Branding/ventana.

Editor visual de rutinas:
- Color con swatches + HEX + sliders HSV.
- Blanco con slider cálido/frío y presets.
- Brillo con slider.
- Escena con selector por nombre + velocidad.
- Favorito, escena personalizada, otra rutina, espera y destino.
- Reordenar acciones con subir/bajar.
