# Validación manual de una release

Prueba el **paquete publicado**, no solo el código fuente. Descárgalo desde
[GitHub Releases](https://github.com/yvvvl/WizzController/releases/latest),
verifica el `.sha256` correspondiente al ZIP/tar, extrae el archivo completo
y cierra otras instancias de WizZ Desktop antes de abrirlo. Respalda tu
configuración si necesitas conservarla. Para cada punto anota PASS, FAIL o
N/A, con el resultado esperado y el real.

## Lista para Windows y Linux

1. **Instalar y abrir:** usa el instalador Windows o el ZIP portable completo;
   en Linux ejecuta `install.sh` para tu usuario. Revisa icono, lanzador,
   bandeja, primer inicio, restauración de instancia única y salida limpia.
2. **Descubrir y seleccionar:** encuentra una ampolleta WiZ real en la misma
   LAN, agrega una IP conocida y selecciona una, varias y todas. Comprueba que
   no quede una selección obsoleta al desconectar o eliminar una luz.
3. **Controlar:** prueba encendido, brillo 20/50/100%, rojo/verde/azul,
   blancos cálido/frío Kelvin y varias escenas WiZ por nombre. Compara el
   resultado físico con la interfaz usando una y varias ampolletas.
4. **Color y favoritos:** usa los pickers RGB y CCT, HEX/Kelvin exactos,
   guarda y reabre favoritos RGB/blanco y comprueba colores recientes.
5. **Rutinas y horarios:** guarda, reordena, reabre y ejecuta una rutina de
   varios pasos. Prográmala para el minuto siguiente con destino fijo
   ampolleta/grupo; revisa el último resultado, páusala y comprueba que no
   vuelva a ejecutarse. Un destino definido en el paso debe prevalecer sobre
   el predeterminado del horario. Las ejecuciones perdidas por suspensión o
   apagado no se recuperan.
6. **Panel rápido e interfaz:** ábrelo desde la bandeja, prueba selección de
   ampolletas en varias páginas y acciones rápidas editables; arrástralo y
   pégalo a los bordes de cada monitor. Confirma posición recordada y cierre
   al hacer clic fuera. Cambia idioma/tema, revisa listas largas y textos,
   reinicia y comprueba persistencia.
7. **Hotkeys:** en Windows, graba una combinación libre, compara `1` del
   teclado principal con `Numpad 1` (Bloq Num activo), usa acciones RGB/Kelvin
   personalizadas y comprueba una ejecución por pulsación. En Linux, verifica
   que la UI avise que todavía no hay hotkeys globales.
8. **Actualización:** desde una instalación anterior compatible, usa
   **Ajustes → Buscar actualización → Instalar y reiniciar**.
   Comprueba descarga y barra de progreso, reinicio en la versión esperada y
   conservación de ajustes. No uses el código fuente para esta prueba.

La bandeja Linux requiere AppIndicator; Wayland forzado puede limitar la
ubicación del panel rápido. Screen Sync/Ambilight y sincronización de audio
no están incluidos: marca N/A. Consulta [instalación](installation.es.md) y
[horarios locales](local-routine-schedules.es.md) para los límites esperados.

## Reporte útil

Incluye versión, sistema operativo y escala, modelo/firmware de la luz,
pasos, resultado esperado y real, repetibilidad y una captura o video corto.
Puedes abrir los logs en **Ajustes → Acerca de → Datos/Logs**. Oculta IP, MAC,
tokens y configuración personal antes de compartir archivos. Reporta en
[GitHub Issues](https://github.com/yvvvl/WizzController/issues).
