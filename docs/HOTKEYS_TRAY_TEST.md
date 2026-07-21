# WizZ Desktop — prueba manual de hotkeys y bandeja

Esta prueba es para Windows real, antes del empaquetado `.exe`. En Flet dev pueden aparecer detalles de ciclo de vida de ventana/tray que no representan el comportamiento final, pero igual sirve para validar lógica.

## 1. Arranque limpio

```powershell
python -m pip install -r requirements.txt
python main.py
```

Validar:

- La app abre sin consola de errores críticos.
- El icono aparece en la bandeja.
- El panel **Hotkeys** muestra `global Windows activo` cuando el backend nativo pudo registrarse.

## 2. Hotkeys globales

Probar una hotkey asignada en cada caso:

- Ventana visible y enfocada.
- Ventana visible pero otra app enfocada.
- Ventana minimizada.
- Ventana oculta a bandeja.
- Pantalla completa borderless, si aplica.

Resultado esperado: la acción debe ejecutarse sin abrir la ventana.

Notas normales de Windows:

- Combinaciones reservadas como `Alt+Tab`, `Win+L`, etc. no se pueden capturar.
- Si controlas una app elevada, WizZ debe correr con permisos equivalentes.
- Secure Desktop/UAC no entrega hotkeys globales a apps normales.

## 3. Menú de bandeja

Validar primero la acción primaria del icono:

- Un clic izquierdo no cambia el estado.
- Doble clic con la ventana visible la oculta a bandeja.
- Doble clic con la ventana oculta o minimizada la restaura.
- Clic derecho continúa abriendo el menú contextual.

Desde el menú de bandeja validar:

- Mostrar WizZ.
- Ocultar a bandeja.
- Encender / Apagar / Alternar.
- Brillo: `+10%`, `-10%`, `25%`, `50%`, `75%`, `100%`.
- Colores / blanco.
- Escenas WiZ.
- Favoritos y rutinas, si existen.
- Re-registrar hotkeys.
- Salir cierra servicios sin dejar proceso zombie.

## 4. Señales de problema

Anotar exactamente qué acción provoca el problema si ves:

- El menú no responde.
- Se pierde el icono de bandeja.
- Las hotkeys pasan a fallback `keyboard`.
- La X destruye la sesión en vez de ocultar.
- Aparece `Session was garbage collected`.

Esos últimos puntos pueden ser limitaciones del modo dev de Flet; conviene revalidarlos en `.exe`.
