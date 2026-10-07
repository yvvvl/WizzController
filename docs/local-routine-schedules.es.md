# Horarios locales para rutinas

WizZ Desktop puede ejecutar una rutina existente a una hora local en los días
de la semana que elijas. Funciona en Windows y Linux sin cuenta ni servicio en
la nube. **La aplicación debe seguir abierta**, aunque esté en la bandeja. Si
el equipo está apagado, suspendido o WizZ no está ejecutándose en ese minuto,
la ejecución se omite. No se recupera después: así no se encienden o apagan
luces inesperadamente al volver al equipo.
Si quieres horarios después de iniciar sesión, activa el inicio con Windows o
Linux en **Ajustes** y deja habilitada la bandeja.

## Cómo usarlo

1. En **Rutinas**, crea o revisa una secuencia. Cada paso puede tener su propio
   destino (una ampolleta o grupo).
2. Baja a **Horarios locales** y pulsa **Nuevo horario**.
3. Escoge la rutina, una hora en formato de 24 horas (`HH:MM`), al menos un día
   y un destino predeterminado: todas las luces, una ampolleta o un grupo
   guardado. Si un paso tiene destino propio, ese destino tiene prioridad.
4. Guarda el horario. Puedes editarlo, pausarlo, reactivarlo o eliminarlo.
   La lista muestra el resultado de la última ejecución. Al borrar una
   rutina, sus horarios quedan desactivados para evitar acciones huérfanas.

Solo se aceptan pasos directos de control de luces, esperas y rutinas anidadas.
Los pasos que dependen de la selección cambiante de la interfaz o de métodos
arbitrarios (favoritos, escenas personalizadas, condiciones, cambio de modo de
destino, métodos personalizados) se rechazan al programar. Siguen disponibles
al ejecutar la rutina manualmente. Esta restricción evita afectar otra luz.

## Comportamiento del reloj

Se usa la fecha, hora y zona horaria del equipo que ejecuta WizZ. Internamente
los días van de lunes=0 a domingo=6. Si un cambio de horario de verano repite
un mismo minuto, la ejecución se realiza como máximo una vez. Si una hora no
existe al adelantar el reloj, se omite. La app revisa los horarios cada 15
segundos mientras está activa; puede haber un pequeño retraso normal del SO.
No despierta el computador suspendido ni crea una tarea externa del sistema.

## Por qué está implementado así

- Los horarios viven en `routine_schedules.json`, dentro del directorio
  persistente normal de la app. El archivo tiene versión y se escribe de forma
  atómica; no se modifica el formato de las rutinas anteriores.
- Antes de enviar los comandos, se registra en disco que ese minuto ya fue
  reclamado. Un reinicio de WizZ dentro del mismo minuto no vuelve a ejecutar
  el horario. Si ocurre un cierre abrupto justo después de registrar el
  minuto, esa ejecución puede perderse: es una política explícita de **como
  máximo una vez**, no una promesa de entrega garantizada.
- Si el archivo tiene datos corruptos o una versión futura, WizZ lo conserva
  sin sobrescribirlo, desactiva los horarios y muestra un error. El resto de
  la app sigue funcionando.
- La secuencia se ejecuta fuera del hilo de la interfaz. El bloqueo de rutinas
  existente evita que dos secuencias se entremezclen. Los destinos de grupos
  se resuelven al ejecutar, de modo que editar un grupo actualiza sus próximas
  ejecuciones.
- Todo queda en el equipo. Se usa el control LAN WiZ existente. Si no hay
  destino disponible, se registra un fallo, no un falso éxito. Un resultado
  correcto significa que el controlador local aceptó los comandos; no
  certifica una confirmación física de cada ampolleta.

## Cómo probar sin tocar la ampolleta real

En Windows, desde el repositorio:

```powershell
$env:WIZZ_DEV_VIRTUAL_BULBS = "3"
try { .\.venv\Scripts\python.exe -m qt_ui.run }
finally { Remove-Item Env:WIZZ_DEV_VIRTUAL_BULBS }
```

En Linux, usa `WIZZ_DEV_VIRTUAL_BULBS=3 PYTHONPATH="$PWD" .venv312/bin/python
-m qt_ui.run`. Crea un horario para el siguiente minuto local y deja WizZ
abierto. Comprueba que la rutina se ejecuta una vez y que la lista cambia a
«Última ejecución correcta». Repite con un horario pausado. El modo virtual no
envía tráfico WiZ y no demuestra entrega a una ampolleta real; esa prueba debe
hacerse por separado.

Pruebas automatizadas: `python -m pytest -q
tests/test_local_routine_scheduler.py tests/test_qt_bridge.py
tests/test_update_installer.py`.

El visor de progreso de actualización de Windows ahora se guarda como UTF-8
con BOM, necesario para que Windows PowerShell 5.1 lea bien los acentos.
Título, estado inicial y estados posteriores siguen el idioma configurado.
