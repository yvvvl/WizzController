# WizZ Controller / WizZ Desktop

Aplicación de escritorio en **Python + Flet 0.85.2** para controlar ampolletas
WiZ directamente por LAN, sin depender de la nube para las acciones normales.

**Versión preparada:** `1.0.0` · build `1`

## Funciones principales

- Control WiZ local por UDP (`setPilot`, `getPilot`, `getSystemConfig`).
- Discovery híbrido: UDP local + `pywizlight` como apoyo.
- Modo **una ampolleta** o **todas**.
- Sincronización de estado con cambios externos y la app móvil.
- Paneles: Inicio, Color Studio, Escenas, Favoritos, Rutinas, Ajustes y Hotkeys.
- Color Studio con picker HSV, HEX/RGB, recientes, armonías y blancos Kelvin.
- Rutinas compuestas con color, blanco, brillo, escenas y espera.
- Hotkeys globales con `RegisterHotKey` nativo y fallback selectivo `keyboard`.
- Bandeja con encendido, brillo, colores, escenas, favoritos y rutinas.
- Instancia única con recuperación de ventana y reemplazo de sesión dev zombie.
- UI responsive desde `720 × 540` hasta pantalla maximizada.

## Desarrollo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python main.py
```

Verificación:

```powershell
python -m compileall -q main.py app_meta.py core config ui tests tools
python -m pytest -q
```

O:

```powershell
.\scripts\verify_repo.ps1
```

> `python main.py` sigue siendo modo de desarrollo. Tray, taskbar, restore,
> icono y FPS finales deben validarse con la build nativa.

## Build `.exe` de Windows

La build oficial usa `flet build windows`, no PyInstaller. Flet genera una
aplicación Windows nativa con el runtime Python y los assets empaquetados.

Requisitos principales:

- Windows 10/11 x64;
- Python 3.11 recomendado;
- Visual Studio 2022 con **Desktop development with C++**;
- Developer Mode cuando Flutter necesite symlinks.

Comando:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1 -Clean
```

Salidas:

```text
dist/windows/WizZDesktop.exe
dist/windows/BUILD_INFO.json
dist/release/WizZDesktop-v1.0.0-windows-x64.zip
dist/release/WizZDesktop-v1.0.0-windows-x64.zip.sha256
```

El EXE necesita los archivos que Flet genera junto a él. La primera distribución
se entrega como ZIP completo.

Prueba rápida de la build:

```powershell
.\scripts\test_windows_build.ps1 -LaunchSecondInstance
```

Guía detallada:

```text
docs/WINDOWS_BUILD.md
```

El workflow **Build Windows** genera el artifact desde un runner Windows al
subir una rama `release/**`, al ejecutar manualmente el workflow o al crear un
tag `v*`.

## Datos persistentes

En desarrollo, los JSON reales viven en:

```text
config/json/
```

En el ejecutable, WizZ usa `FLET_APP_STORAGE_DATA`, el directorio persistente que
Flet conserva entre actualizaciones. Allí se guardan:

```text
config/*.json
logs/wizz.log
```

La ubicación exacta se abre desde **Ajustes → Acerca de → Datos/Logs**. Al primer
arranque empaquetado, WizZ puede migrar los JSON de desarrollo si encuentra el
repositorio y el storage nuevo está vacío.

Los JSON reales no se versionan porque pueden contener IP, MAC y hotkeys. Los
archivos `config/json/*.example.json` son ejemplos seguros.

## Color Studio

El panel Color incluye:

```text
picker HSV visual calibrado
barra de matiz
HEX/RGB exacto
modo aplicar en vivo
recientes persistentes
armonías y paletas inteligentes
moods visuales
blancos por Kelvin
favoritos rápidos
```

El brillo se mantiene separado del color RGB porque WiZ usa `dimming` como canal
propio. Los arrastres usan throttle y protección de coordenadas para alcanzar
0%/100% sin saltar al borde opuesto.

Checklist responsive y visual:

```text
docs/RESPONSIVE_UI_TEST.md
```

## Hotkeys

En Windows se usa primero `RegisterHotKey`. Si solo una combinación está ocupada,
las demás permanecen nativas y únicamente esa combinación usa el fallback.

Ejemplos recomendados:

```text
ctrl+alt+l
ctrl+alt+up
ctrl+alt+down
shift+f8
```

Combinaciones bloqueadas:

```text
alt+tab
alt+f4
win+l
ctrl+alt+del
ctrl+shift+esc
```

Diagnóstico sin abrir la UI:

```powershell
python tools/desktop_selftest.py
python tools/desktop_selftest.py --register-test ctrl+alt+shift+f12 --seconds 10
python tools/desktop_selftest.py --listen-current --seconds 15
python tools/desktop_runtime_probe.py
```

## Git y release

La fase v1 debe trabajarse en una rama de release con commits pequeños, tests
verdes y un smoke test del artifact antes de crear el tag final. La guía segura para conectar el repositorio, crear rama, hacer commits,
push y tag está en:

```text
docs/GIT_RELEASE_WORKFLOW.md
```

Repositorio:

```text
https://github.com/yvvvl/WizzController
```

## Estructura

```text
app_meta.py  nombre, versión e identificadores de producto
core/        WiZ, secuencias, hotkeys, instancia única, tray y logging
config/      managers JSON y rutas persistentes
ui/          aplicación y paneles Flet
assets/      iconos y recursos visuales
docs/        checklists y guías de release
scripts/     verificación y build Windows
tools/       utilidades de diagnóstico
tests/       regresiones del core, UI y packaging
```
