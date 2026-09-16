<div align="center">

**Español** · [English](README.md)

<img src="assets/icon_windows.png" alt="WizZ Desktop" width="112" />

# WizZ Desktop

### Control local, rápido y privado para ampolletas WiZ

[![Release](https://img.shields.io/github/v/release/yvvvl/WizzController?label=release)](https://github.com/yvvvl/WizzController/releases/latest)
[![CI](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/ci.yml)
[![Windows Build](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml/badge.svg)](https://github.com/yvvvl/WizzController/actions/workflows/build-windows.yml)
[![Python](https://img.shields.io/badge/Python-3.11%20%E2%80%93%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/UI-Qt%20%2F%20PySide6-41CD52)](https://www.qt.io/)

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
- Canales Estable/Beta y actualización automática verificada en Windows
  portable, desde la versión 1.3.0.
- Configuración y logs persistentes en AppData Local para builds Windows.
- Restauración más predecible de la ventana desde la bandeja.
- Validación real de control WiZ, tray, hotkeys, instancia única y ejecutable
  aislado en Windows.
- Beta Linux: persistencia XDG, bandeja AppIndicator en GNOME/Wayland,
  apertura de Datos/Logs y arranque automático por usuario.

> Screen Sync, streaming y actualización automática no están incluidos
> en esta versión estable.

## Beta cerrada v1.4.0b1 — guía para pruebas

Esta sección aplica únicamente a la **preview Qt privada**. Es distinta de la
versión estable pública y requiere una cuenta de GitHub invitada. Es una build
portable de Windows: no la ejecutes dentro del ZIP y mantén `_internal` junto a
`WizZDesktop.exe`.

### Comandos para instalar y abrir (Windows PowerShell)

Descarga `WizZDesktop-v1.4.0b1-windows-x64.zip` y su archivo `.sha256` desde la
release privada. Luego ejecuta lo siguiente. Cambia `$download` solo si los
archivos no quedaron en Descargas.

```powershell
$download = "$env:USERPROFILE\Downloads"
$zip = Join-Path $download "WizZDesktop-v1.4.0b1-windows-x64.zip"
$checksum = "$zip.sha256"
$target = Join-Path $download "WizZDesktop-v1.4.0b1"

Get-FileHash -LiteralPath $zip -Algorithm SHA256
Get-Content -LiteralPath $checksum
Expand-Archive -LiteralPath $zip -DestinationPath $target -Force
Set-Location $target
.\WizZDesktop.exe
```

El hash que muestra `Get-FileHash` debe coincidir con el hash del archivo
`.sha256`. Antes de probar, cierra todas las demás copias de WizZ Desktop y
respalda `%LOCALAPPDATA%\WizZDesktop` si quieres conservar su configuración:
esta beta usa la misma carpeta de datos local.

### Qué debe probar

Usa ampolletas WiZ reales en la misma red local cuando sea posible. En cada
prueba anota **PASS**, **FAIL** o **N/A**, junto con el resultado esperado y el
resultado real.

1. **Conexión y selección:** en Ajustes busca ampolletas y prueba también
   agregar una IP conocida manualmente. Selecciona una, varias y todas.
2. **Controles de Inicio:** alterna encendido; prueba 20%, 50% y 100% de
   brillo; aplica rojo, verde, azul, blanco cálido y blanco frío. Confirma que
   el resultado físico coincide con la interfaz, en una y varias ampolletas.
3. **Nueva interfaz:** redimensiona la ventana, cambia temas y revisa listas
   largas, tarjetas, textos centrados en opciones, listas redondeadas y el
   tintado del tema. Reinicia y confirma que se conservan tema e ítems guardados.
4. **Favoritos y Color:** crea favoritos RGB y blancos CCT. Prueba los colores
   rápidos, campo HEX/Kelvin, cursor del picker, vista previa, guardar, reabrir
   y aplicar cada favorito.
5. **Escenas y rutinas:** crea una escena local por nombre (no por ID). Crea una
   rutina con encendido, color RGB, blanco CCT, espera y escena; reordénala,
   guárdala, ábrela de nuevo y ejecútala. Aplica varias escenas WiZ por nombre.
6. **Panel rápido:** ábrelo con su atajo configurado, usa el carrusel de
   ampolletas, selecciona ampolletas de páginas posteriores y confirma que no
   vuelve a la primera página. Prueba flechas/botones de página, posición junto
   a la barra de tareas en cada monitor, cierre al hacer clic fuera y accesos
   rápidos editados.
7. **Hotkeys y bandeja:** asigna un atajo que no choque con otro programa,
   reinicia y confirma una sola acción por pulsación y sin congelamientos. Prueba
   restaurar desde la bandeja y el comportamiento de cerrar/minimizar.

### Integraciones y límites conocidos

- **WiZ LAN:** discovery, IP manual, encendido, brillo, RGB, blanco CCT,
  escenas con nombre, selección múltiple, favoritos, rutinas, bandeja y hotkeys
  son las integraciones que hay que ejercitar.
- **Cambios desde la app móvil WiZ:** si cambias una luz desde el teléfono,
  registra si la app de escritorio lo refleja y cuánto tarda. Es una prueba
  observacional, no una garantía para todos los modelos o firmwares.
- **No incluido:** Screen Sync/Ambilight, sincronización de audio, efectos
  experimentales para tiras, bucle de FPS y autoactualización de beta privada. No los
  reportes como fallas; márcalos como **N/A**.

### Comandos opcionales para probar desde el código (solo colaboradores)

No uses estos comandos para validar el ZIP descargado. Son únicamente para un
tester al que se le dio acceso explícito al repositorio fuente:

```powershell
git clone https://github.com/yvvvl/WizzController-Beta.git
Set-Location .\WizzController-Beta
git switch beta/v1.4.0
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m qt_ui.run
python -m pytest -q
```

### Cómo enviar un reporte útil

Incluye versión (`1.4.0b1`), versión de Windows y escala de pantalla, modelo y
firmware de la ampolleta, pasos exactos, esperado versus real, repetibilidad y
una captura/video corto cuando ayude. Para ver el log local sin compartir los
archivos de configuración privada:

```powershell
Get-Content "$env:LOCALAPPDATA\WizZDesktop\logs\wizz.log" -Tail 200
```

Oculta IPs, MACs, tokens y archivos de la beta antes de enviar información
fuera del grupo invitado. El checklist completo en inglés también está adjunto
a la release privada como `BETA_TESTING_EN.md`.

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
2. Descarga el archivo `WizZDesktop-v*-windows-x64.zip` de la release elegida.
3. Extrae todo el contenido del ZIP.
4. Ejecuta `WizZDesktop.exe`.

> No ejecutes el programa directamente dentro del ZIP y no separes el `.exe` de las DLL ni de la carpeta `data`.

La descarga incluye un archivo `.sha256` para comprobar la integridad del paquete.

Después de instalar v1.3.0 o posterior puedes elegir **Estable** o **Beta** en
**Ajustes → Actualizaciones**. La app descarga, verifica e instala el siguiente
ZIP oficial al reiniciar. El canal Beta queda preparado para recibir
pre-releases de una distribución privada antes que Estable.

> Una beta cerrada no se publica como release de este repositorio público. Para
> compartirla con personas seleccionadas se usa una distribución privada con
> cuentas o accesos individuales; un código dentro de la app no vuelve privada
> una descarga pública.

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
- Qt for Python / PySide6.
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
python -m qt_ui.run
```

> `python main.py` también abre Qt para compatibilidad. Flet ya no es una ruta de ejecución ni de distribución pública.

### Validar el repositorio

```powershell
python -m compileall -q main.py app_meta.py core config qt_ui tests tools
python -m pytest -q
```

También puedes usar:

```powershell
.\scripts\verify_repo.ps1
```

---

## Build nativa para Windows

WizZ Desktop utiliza PyInstaller con Qt; Flet no se empaqueta.

### Requisitos adicionales

- Visual Studio con **Desktop development with C++**.
- SDK de Windows.
- Developer Mode cuando Flutter requiera crear enlaces simbólicos.

### Generar la build

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_qt_windows.ps1 -Clean
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

Las instalaciones Flet anteriores se migran automáticamente la primera vez que
se ejecuta esta versión, pero Flet ya no se inicia ni se empaqueta para usuarios.

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
