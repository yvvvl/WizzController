# v1 RC — restauración de ventana e instancia única

## Problema corregido

La restauración anterior llamaba `Window.to_front()` desde el thread del tray o
del listener de instancia única. Si el cliente desktop de Flet ya había cerrado
su sesión, el loop estaba cerrado y quedaban estos síntomas:

```txt
Event loop is closed
coroutine ... was never awaited
Window.to_front was never awaited
```

## Comportamiento nuevo

- Una segunda ejecución busca la ventana Win32 perteneciente al proceso Flet de
  la instancia activa y la restaura directamente.
- El modelo `visible/minimized/focused` de Flet se sincroniza únicamente cuando
  su loop sigue vivo.
- No se crea el coroutine `Window.to_front()` desde pystray.
- Si Flet terminó pero el proceso Python/tray quedó vivo, la nueva ejecución
  solicita un relevo: se detienen hotkeys, WiZ y tray, se libera el mutex y se
  inicia una sesión limpia.
- Cuando `ft.run()` termina, el proceso principal detiene explícitamente los
  servicios para no dejar un tray zombie.

## Prueba rápida en Windows

1. Ejecuta `python main.py`.
2. Oculta WizZ con la X.
3. Ejecuta `python main.py` de nuevo.
4. Repite con la ventana visible y minimizada.
5. Sal desde el menú de bandeja y revisa el Administrador de tareas.

Resultado esperado:

- la ventana original vuelve al frente;
- no aparece una segunda ventana, tray ni registro de hotkeys;
- la segunda consola termina sola;
- no aparece ningún warning de coroutine o loop cerrado;
- al usar **Salir**, no queda `python.exe`, `pythonw.exe` ni cliente Flet de WizZ.
