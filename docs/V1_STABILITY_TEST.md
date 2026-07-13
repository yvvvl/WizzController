# Cierre de v1 — estabilidad desktop

Ejecuta estas pruebas en Windows con una sola carpeta de WizZ Desktop.

## 1. Instancia única

1. Abre `python main.py`.
2. Oculta la ventana con la X si la bandeja está activa.
3. Ejecuta `python main.py` nuevamente.

Resultado esperado:

- no aparece una segunda ventana ni un segundo tray;
- la instancia que ya estaba abierta se restaura y queda al frente;
- el segundo proceso termina por sí solo;
- las hotkeys siguen indicando `Windows nativo activo · N/N`;
- no aparecen `Event loop is closed` ni avisos `coroutine was never awaited`.

La restauración usa primero la ventana Win32 real del cliente Flet. No llama
`Window.to_front()` desde el thread del tray.

### Recuperación de tray zombie en modo dev

Esta prueba reproduce el caso más agresivo de `python main.py`:

1. Abre WizZ normalmente.
2. En el Administrador de tareas, termina solo el cliente desktop de Flet y deja
   vivo el proceso Python/tray.
3. Ejecuta `python main.py` otra vez.

Resultado esperado:

- la segunda ejecución espera brevemente una ventana restaurable;
- normalmente el proceso Python detecta el cierre del cliente Flet y detiene tray,
  hotkeys y WiZ por sí solo;
- si aun así quedó vivo, la segunda ejecución solicita un relevo;
- el proceso zombie sale y se inicia una sesión limpia;
- queda un solo icono de bandeja y un solo servicio de hotkeys.

## 2. Re-registro limpio de hotkeys

1. Abre **Hotkeys**.
2. Pulsa **Re-registrar** varias veces, dejando uno o dos segundos entre cada clic.
3. Prueba cada combinación con otra aplicación enfocada.

Resultado esperado:

- no aparecen disparos dobles;
- no aparece un conflicto causado por WizZ contra sí mismo;
- el contador se mantiene, por ejemplo `Windows nativo activo · 3/3`.

Cuando otra aplicación ocupa una combinación, WizZ puede mostrar:

```txt
Windows + fallback activo · 3/3
1 atajo usa fallback keyboard; los demás usan Windows nativo.
```

Solo la combinación conflictiva usa fallback; las demás conservan `RegisterHotKey`.

## 3. Bandeja y cierre real

1. Pulsa la X: WizZ debe ocultarse, no cerrarse.
2. Usa **Mostrar WizZ** desde la bandeja.
3. Prueba encender, brillo, color o una escena desde el menú.
4. Usa **Salir** desde la bandeja.

Resultado esperado:

- el icono desaparece;
- las hotkeys dejan de responder;
- no queda `python.exe`, `pythonw.exe` ni WizZ en el Administrador de tareas.

## 4. Suspensión de Windows

1. Deja WizZ oculto en bandeja.
2. Suspende el equipo y vuelve a iniciar sesión.
3. Prueba una hotkey y abre el menú de bandeja.
4. Si una hotkey no responde, pulsa **Re-registrar** una vez.

Anota cualquier caso que requiera re-registro; esto definirá si la v1 necesita una reactivación automática después de suspensión.
