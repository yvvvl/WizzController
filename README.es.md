<div align="center">

**Español** · [English](README.md)

<img src="assets/icon_windows.png" alt="WizZ Desktop" width="112" />

# WizZ Desktop

### Control local, rápido y privado para ampolletas WiZ

[![Release](https://img.shields.io/github/v/release/yvvvl/WizzController?label=release)](https://github.com/yvvvl/WizzController/releases/latest)
[![CI](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml)
[![Windows Build](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml)
[![Python](https://img.shields.io/badge/Python-3.11%20%E2%80%93%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.85.2-6C63FF)](https://flet.dev/)

[Descargar última versión](https://github.com/yvvvl/WizzController/releases/latest) · [Reportar un problema](https://github.com/yvvvl/WizzController/issues)

</div>

---

## Qué es WizZ Desktop

**WizZ Desktop** es una aplicación de escritorio para controlar ampolletas WiZ directamente dentro de la red local.

Las acciones normales se envían por **UDP LAN nativo**, por lo que el control no depende de la nube de WiZ y mantiene una respuesta rápida incluso cuando la conexión a Internet no está disponible.

La aplicación combina control de iluminación, automatizaciones y una interfaz
moderna en un único programa portable. Windows es la plataforma estable;
Linux se entrega como beta para Ubuntu Desktop y otros escritorios compatibles.

> Versión pública actual: **v1.2.0 · build 2**

## Novedades v1.2.0

- Selección temporal de una, varias o todas las ampolletas.
- Comprobación manual y segura de actualizaciones desde GitHub Releases.
- Configuración y logs persistentes en AppData Local para builds Windows.
- Restauración más predecible de la ventana desde la bandeja.
- Validación real de control WiZ, tray, hotkeys, instancia única y ejecutable
  aislado en Windows.
- Beta Linux: persistencia XDG, bandeja AppIndicator en GNOME/Wayland,
  apertura de Datos/Logs y arranque automático por usuario.

> RGBIC, Screen Sync, streaming y actualización automática no están incluidos
> en esta versión estable.

---

## Funciones principales

### Control local WiZ

- Encendido, apagado y alternancia.
- Brillo independiente mediante `dimming`.
- Colores RGB.
- Blancos configurables por temperatura Kelvin.
- Escenas oficiales WiZ.
- Sincronización con cambios realizados desde la aplicación móvil.
- Control de una ampolleta específica o de todas las detectadas.

### Color Studio

- Paleta perceptual de matiz y pureza.
- Color visible y valor enviado calculados desde la misma fuente.
- Brillo separado del RGB.
- Blancos Kelvin separados del modo color.
- Edición precisa mediante HEX, RGB, H y S.
- Aplicación en vivo o manual.
- Colores recientes, favoritos y presets.
- Conversión del color lógico hacia los canales físicos RGBTW de WiZ.
- Arrastre fluido con protección de bordes y coordenadas fuera del picker.

### Automatización

- Favoritos para acciones rápidas.
- Rutinas con múltiples pasos.
- Acciones compatibles:
  - color;
  - blanco;
  - brillo;
  - escena;
  - espera.
- Ejecución centralizada mediante `ActionSequenceExecutor`.

### Integración de escritorio

- Hotkeys globales nativas mediante `RegisterHotKey`.
- Fallback selectivo usando `keyboard` cuando una combinación está ocupada.
- System tray con acciones rápidas.
- Un clic en el icono de bandeja para restaurar la ventana principal.
- Cierre a bandeja.
- Inicio minimizado.
- Inicio automático con Windows.
- Instancia única con restauración de la ventana existente.
- Beta Linux con bandeja AppIndicator, persistencia XDG, autostart por usuario
  e instalador sin `sudo`.
- Hotkeys globales deshabilitadas explícitamente en Linux cuando el escritorio
  no ofrece un portal seguro compatible.

### Gestión de ampolletas

- Discovery híbrido mediante UDP local y `pywizlight` como apoyo.
- Búsqueda por broadcast e interfaces de red.
- Adición manual por IP.
- Renombrado de dispositivos.
- Eliminación persistente.
- Redescubrimiento explícito mediante **Buscar ampolletas**.
- Protección contra respuestas tardías que puedan volver a registrar un dispositivo eliminado.

---

## Instalación para usuarios

### Windows estable — requisitos

- Windows 10 u 11 de 64 bits.
- Una ampolleta WiZ conectada a la misma red local que el PC.

### Pasos

1. Abre la [última release](https://github.com/yvvvl/WizzController/releases/latest).
2. Descarga `WizZDesktop-v1.2.0-windows-x64.zip`.
3. Extrae todo el contenido del ZIP.
4. Ejecuta `WizZDesktop.exe`.

> No ejecutes el programa directamente dentro del ZIP y no separes el `.exe` de las DLL ni de la carpeta `data`.

La descarga incluye un archivo `.sha256` para comprobar la integridad del paquete.

### Linux beta — Ubuntu Desktop

La beta Linux se distribuye como `WizZDesktop-v1.2.0-linux-x64.tar.gz` con su
archivo `.sha256`. Extrae el archivo, abre una terminal dentro de la carpeta
extraída y ejecuta `./install.sh`. No requiere `sudo`: instala la app para tu
usuario, crea el acceso **WizZ Desktop** en Aplicaciones y conserva tus datos
al actualizar. Luego puedes abrirla desde Actividades y anclarla al dock.

Para retirar la aplicación instalada, ejecuta
`~/.local/share/WizZDesktop/uninstall.sh`. Esto elimina la app y su lanzador,
pero conserva tus configuraciones, ampolletas, favoritos y logs.

También puedes ejecutar `./WizZDesktop` directamente desde la carpeta
extraída si prefieres usarla en modo portable. La plataforma validada es Ubuntu
Desktop con GNOME; en Wayland, la posición de ventana la decide el compositor.

La bandeja requiere un escritorio compatible con AppIndicator. Si no está
disponible, la aplicación sigue siendo usable como ventana normal. Los hotkeys
globales están deshabilitados intencionalmente en Linux beta hasta contar con
un backend seguro basado en el portal XDG.

### Verificar SHA-256 en PowerShell

```powershell
Get-FileHash .\WizZDesktop-v1.2.0-windows-x64.zip -Algorithm SHA256
```

Compara el resultado con el contenido de:

```text
WizZDesktop-v1.2.0-windows-x64.zip.sha256
```

---

## Uso básico

1. Abre **Ajustes**.
2. Pulsa **Buscar ampolletas**.
3. Selecciona la ampolleta activa.
4. Controla la luz desde **Inicio**, **Color** o **Escenas**.
5. Configura favoritos, rutinas y hotkeys según tu flujo.

Si eliminas una ampolleta, permanecerá fuera de la lista hasta que realices una búsqueda explícita o la agregues nuevamente por IP.

---

## Desarrollo

### Requisitos

- Python `>=3.11,<3.14`.
- Flet `0.85.2`.
- Windows para la build estable de Windows.
- Ubuntu Desktop o WSL para la build beta Linux.

### Preparar el entorno

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### Ejecutar en modo desarrollo

```powershell
python main.py
```

> El modo `python main.py` es útil para desarrollo, pero tray, taskbar, restauración de ventana, iconos y comportamiento final deben validarse también en la build nativa.

### Validar el repositorio

```powershell
python -m compileall -q main.py app_meta.py core config ui tests tools
python -m pytest -q
```

También puedes usar:

```powershell
.\scripts\verify_repo.ps1
```

---

## Build nativa para Windows

WizZ Desktop utiliza `flet build windows`; no usa PyInstaller.

### Requisitos adicionales

- Visual Studio con **Desktop development with C++**.
- SDK de Windows.
- Developer Mode cuando Flutter requiera crear enlaces simbólicos.

### Generar la build

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1 -Clean
```

### Salidas

```text
dist/windows/WizZDesktop.exe
dist/windows/BUILD_INFO.json
dist/release/WizZDesktop-v1.2.0-windows-x64.zip
dist/release/WizZDesktop-v1.2.0-windows-x64.zip.sha256
```

### Smoke test

```powershell
.\scripts\test_windows_build.ps1 -LaunchSecondInstance
```

La guía completa está en
[`docs/codex/plans/2026-07-21-windows-build.md`](docs/codex/plans/2026-07-21-windows-build.md).

---

## Build nativa para Linux beta

En Ubuntu 22.04 instala las dependencias de compilación y AppIndicator:

```bash
sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev \
  lld-14 libcairo2-dev libgirepository1.0-dev \
  gir1.2-ayatanaappindicator3-0.1
```

Luego crea el entorno Python del proyecto e instala sus dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-build.txt
```

Finalmente ejecuta:

```bash
source .venv/bin/activate
bash scripts/build_linux.sh --clean
```

Las salidas son:

```text
dist/linux/WizZDesktop
dist/linux/BUILD_INFO.json
dist/linux/install.sh
dist/linux/uninstall.sh
dist/release/WizZDesktop-v1.2.0-linux-x64.tar.gz
dist/release/WizZDesktop-v1.2.0-linux-x64.tar.gz.sha256
```

---

## Datos y privacidad

WizZ Desktop no necesita una cuenta propia ni una base de datos remota para controlar las luces por LAN.

En desarrollo, los archivos locales viven en:

```text
config/json/
```

En el ejecutable Windows, configuraciones y logs se guardan en:

```text
%LOCALAPPDATA%\WizZDesktop
```

Las instalaciones Flet previas se migran automáticamente la primera vez que
se ejecuta esta versión.

En Linux, la configuración y los logs respetan las rutas XDG:

```text
~/.config/WizZDesktop/config
~/.local/state/WizZDesktop/logs
```

El instalador por usuario guarda la aplicación bajo
`~/.local/share/WizZDesktop` y crea un acceso directo en el menú de
aplicaciones.

Puedes abrir las ubicaciones reales desde:

```text
Ajustes → Acerca de → Datos
Ajustes → Acerca de → Logs
```

Los JSON personales no se versionan porque pueden contener:

- direcciones IP;
- direcciones MAC;
- hotkeys;
- preferencias locales.

El repositorio conserva únicamente archivos `*.example.json` seguros.

---

## Arquitectura

```text
UI / Tray / Hotkeys / Favoritos / Rutinas
                    │
                    ▼
         ActionSequenceExecutor
                    │
                    ▼
             LightController
                    │
                    ▼
          UDP LAN nativo WiZ :38899
```

Principios del proyecto:

- control local como camino principal;
- `setPilot` fire-and-forget para baja latencia;
- lectura y verificación fuera del hot path;
- una sola capa de ejecución para acciones;
- configuración persistente y segura ante escrituras concurrentes;
- UI optimizada para evitar repaints innecesarios.

---

## Estructura del repositorio

```text
app_meta.py   Metadatos, versión e identificadores del producto
core/         WiZ, acciones, hotkeys, tray, instancia única y logging
config/       Configuración persistente y managers JSON
ui/           Aplicación y componentes Flet
assets/       Iconos y recursos visuales
docs/         Guías y checklists
scripts/      Verificación, instaladores y builds de Windows/Linux
tools/        Diagnósticos y probes
tests/        Pruebas de core, UI, runtime y packaging
```

---

## Diagnóstico

### Hotkeys y runtime de escritorio

```powershell
python tools/desktop_selftest.py
python tools/desktop_runtime_probe.py
```

### Pipeline de color WiZ

```powershell
python tools/wiz_color_probe.py --hex FFAD9E
```

### Eliminación activa de ampolletas

```powershell
python tools/probe_remove_active_bulb.py --ip 192.168.1.4
```

---

## Estado del proyecto

La versión pública `v1.2.0` ofrece una build estable portable para Windows x64
y la primera beta nativa para Linux x64. El siguiente ciclo, `v1.3.0`, se
enfoca en refactorizar la interfaz sin perder la estabilidad alcanzada.

El proyecto cuenta con pruebas automatizadas para:

- control y targeting;
- Color Studio;
- pipeline RGBTW;
- persistencia concurrente;
- eliminación y redescubrimiento;
- responsive UI;
- hotkeys;
- tray e instancia única;
- packaging de Windows y Linux.

---

## Autor

Desarrollado por **Ignacio** (`yvvvl`).

Proyecto construido como una aplicación personal de escritorio para control local de iluminación WiZ.


---

## Acknowledgements

WizZ Desktop uses:

- `pywizlight` by Stephan Traub and contributors.

See:

- `THIRD_PARTY_NOTICES.md`
- `licenses/pywizlight-LICENSE.txt`

for license information.

WizZ Desktop is an independent community project and is not
affiliated with WiZ Connected or Signify.
