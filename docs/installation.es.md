# Instalar y actualizar WizZ Desktop

Descarga la versión estable desde [GitHub Releases](https://github.com/yvvvl/WizzController/releases/latest).
Son compatibles Windows 10/11 x64 y escritorios Linux compatibles con Ubuntu
en x64 o ARM64. macOS sigue siendo experimental y no tiene descarga oficial.
El PC y las ampolletas WiZ deben estar en la misma red local.

## Windows

- El archivo `windows-x64-setup.exe` instala WizZ Desktop. El instalador y la
  aplicación todavía no tienen firma digital; Windows puede mostrar
  SmartScreen. Comprueba que los descargaste de este repositorio.
- Como alternativa, extrae todo el archivo `windows-x64.zip` y abre
  `WizZDesktop.exe`. Mantén `_internal` junto al ejecutable; no lo abras
  dentro del ZIP. El ZIP portable tiene un archivo `.sha256` correspondiente.
- En instalaciones portables compatibles, **Ajustes → Buscar actualización →
  Instalar y reiniciar** descarga e instala la versión
  estable desde la app. Respalda tu configuración antes de un cambio mayor.

Para comprobar el ZIP, ejecuta `Get-FileHash` sobre el archivo descargado en
PowerShell y compara su SHA-256 con el `.sha256` adjunto. El instalador `.exe`
no tiene, por ahora, un archivo de checksum separado.

## Linux (x64 y ARM64)

Elige `linux-x64.tar.gz` para Intel/AMD o `linux-arm64.tar.gz` para ARM de 64
bits. Verifica su `.sha256`, extrae el paquete y ejecuta `./install.sh` dentro
de la carpeta extraída. Se instala para tu usuario, sin `sudo`. Abre **WizZ
Desktop** desde Aplicaciones y, si quieres, ancla el icono al dock. La
configuración y los logs se conservan al actualizar o desinstalar.

La instalación puede actualizarse desde **Ajustes → Buscar actualización →
Instalar y reiniciar**. También puedes ejecutar
`./WizZDesktop` directamente desde la carpeta extraída, aunque eso no usa la
instalación gestionada.

Para desinstalar la copia de tu usuario, ejecuta
`~/.local/share/WizZDesktop/uninstall.sh`. Elimina la app y su lanzador, pero
no tu configuración ni tus logs.

En Wayland, WizZ Desktop prefiere XWayland si están disponibles las bibliotecas
XCB de Qt para posicionar y pegar el panel rápido a los bordes. Si faltan,
instala `libxcb-cursor0`, `libxcb-icccm4` y `libxcb-keysyms1`. Si se fuerza
Wayland, la ubicación queda a cargo del compositor. La bandeja requiere un
escritorio compatible con AppIndicator; sin ella, la ventana principal sigue
disponible. Los hotkeys globales aún no funcionan en Linux: no ejecutes la app
como root para intentar activarlos.

## Verificación y datos guardados

En Linux usa `sha256sum -c <archivo>.sha256`; en Windows, compara
`Get-FileHash` con el archivo adjunto. Ejecuta solo paquetes de la release
oficial.

| Instalación | Configuración y logs |
| --- | --- |
| Windows | `%LOCALAPPDATA%\WizZDesktop\config` y `%LOCALAPPDATA%\WizZDesktop\logs` |
| Linux | `~/.config/WizZDesktop/config` y `~/.local/state/WizZDesktop/logs` |

Abre las ubicaciones reales desde **Ajustes → Acerca de → Datos/Logs**. Los
datos de versiones Flet anteriores se migran cuando corresponde. Los JSON
locales pueden contener IP, MAC y preferencias; no los publiques en reportes.
