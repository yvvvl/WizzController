# Desarrollo y validación de WizZ Desktop

La entrada de escritorio compatible es `python -m qt_ui.run`. Usa Python
3.11–3.13; el flujo Linux compila con Python 3.12. No hagas pruebas con una
ampolleta real si quieres usar el modo virtual.

## Preparar el código fuente

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m qt_ui.run
```

Linux (usa Python 3.12 aunque la distribución traiga una versión más nueva):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-qt-linux.txt -r requirements-dev.txt
PYTHONPATH="$PWD" .venv/bin/python -m qt_ui.run
```

En Linux también se necesitan bibliotecas del sistema para Qt/XCB y
AppIndicator. La lista vigente está en el trabajo `build-linux` del
[flujo oficial](../.github/workflows/build-windows.yml). La compatibilidad
macOS es experimental y aún no se distribuye públicamente.

## Ampolletas virtuales y pruebas

El código fuente acepta `WIZZ_DEV_VIRTUAL_BULBS=3`: crea tres luces simuladas,
usa un perfil de prueba separado y **no envía tráfico WiZ LAN**. Los paquetes
públicos ignoran esta variable. Sirve para probar varias luces, destinos,
brillo, RGB, Kelvin, escenas, rutinas y horarios sin tener más ampolletas.

```powershell
$env:WIZZ_DEV_VIRTUAL_BULBS = "3"
try { .\.venv\Scripts\python.exe -m qt_ui.run }
finally { Remove-Item Env:WIZZ_DEV_VIRTUAL_BULBS }
```

```bash
WIZZ_DEV_VIRTUAL_BULBS=3 PYTHONPATH="$PWD" .venv/bin/python -m qt_ui.run
```

Antes de proponer cambios, ejecuta:

```bash
python -m compileall -q main.py app_meta.py core config qt_ui localization tests tools
python -m pytest -q
python tools/i18n_audit.py
git diff --check
```

En Windows, `scripts/verify_repo.ps1` sirve como atajo local. La
[lista de validación manual](release-validation.es.md) cubre ampolletas
reales, escritorio y actualizaciones empaquetadas; las pruebas automatizadas
no reemplazan esas comprobaciones. Consulta la [guía para contribuir](../CONTRIBUTING.md)
y la [política del repositorio](repository-maintenance.md) para conocer los
límites del código y qué archivos deben mantenerse solo en tu equipo.

## Rutas actuales y de legado

| Ruta | Función |
| --- | --- |
| `qt_ui/` | Interfaz Qt/PySide6, panel rápido y runtime vigentes. |
| `core/`, `config/`, `localization/` | Control, persistencia, plataforma e idiomas. |
| `scripts/build_qt_windows.ps1`, `scripts/build_qt_linux.sh` | Builds oficiales de Windows/Linux. |
| `.github/workflows/build-windows.yml` | Compilación oficial para tres plataformas y publicación por tag. |
| `scripts/build_qt_macos.sh` | Build Mac experimental, sin firma; solo smoke test. |
| `ui/`, `run_flet_legacy()` en `main.py` | Código Flet conservado por migración y pruebas históricas; no es la interfaz pública. `python main.py` abre Qt. |
| `scripts/build_windows.ps1`, `scripts/build_linux.sh` | Builds Flet retiradas; no usar para una release. |

Flet figura como dependencia opcional `legacy-flet` en `pyproject.toml` y en
los requisitos de desarrollo para pruebas históricas. No se empaqueta en las
releases Qt. No elimines el código legado ni sus pruebas sin revisar antes la
cobertura de migración y las dependencias.

La arquitectura vigente es:

```text
Qt UI / runtime de escritorio
           ↓
servicios y secuencias de acciones
           ↓
control WiZ LAN + configuración JSON persistente
```

## Generar un paquete local equivalente al oficial

Windows (Inno Setup 6 o 7 permite generar el instalador `.exe`):

```powershell
.\scripts\build_qt_windows.ps1 -Clean
.\scripts\test_windows_build.ps1 -LaunchSecondInstance
```

Linux (tras instalar las bibliotecas del sistema y `requirements-build.txt`):

```bash
bash scripts/build_qt_linux.sh --clean
```

Los paquetes resultantes quedan en `dist/release/`. Una ejecución desde el
código fuente o un paquete local no reemplaza la prueba del archivo publicado.
