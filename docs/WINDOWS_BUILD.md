# Build nativo de WizZ Desktop para Windows

La distribución inicial usa el pipeline oficial de Flet:

```text
flet build windows
```

Esto genera una aplicación Flutter/Windows que contiene el runtime Python y el
código de WizZ. No es el mismo entorno que `python main.py`; es la build correcta
para validar icono, taskbar, tray, restore y rendimiento desktop.

## Requisitos en el PC de build

- Windows 10 u 11 de 64 bits.
- Python 3.11 recomendado.
- Visual Studio 2022 con **Desktop development with C++**.
- Developer Mode de Windows habilitado si Flutter solicita soporte de symlinks.
- Conexión a Internet en el primer build para descargar herramientas y wheels.

## Build local

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1 -Clean
```

Para iteraciones posteriores, sin limpiar la caché de Flutter:

```powershell
.\scripts\build_windows.ps1
```

El script realiza:

1. instalación de dependencias de runtime, test y build;
2. `compileall`;
3. `pytest`;
4. `flet build windows`;
5. verificación de `WizZDesktop.exe`;
6. manifiesto `BUILD_INFO.json` con versión, commit y toolchain;
7. ZIP completo de distribución;
8. checksum SHA-256.

Salidas esperadas:

```text
dist/windows/WizZDesktop.exe
dist/windows/BUILD_INFO.json
dist/release/WizZDesktop-v1.0.0-windows-x64.zip
dist/release/WizZDesktop-v1.0.0-windows-x64.zip.sha256
```

> El EXE debe distribuirse con los DLL y archivos que Flet deja a su lado. Para
> la primera versión se entrega el ZIP completo, no un EXE aislado.

## Smoke test asistido

Después de generar la build:

```powershell
.\scripts\test_windows_build.ps1 -LaunchSecondInstance
```

El script comprueba que el launcher siga vivo después del arranque y, de forma
opcional, ejecuta una segunda instancia para validar el flujo de restauración.
Las funciones WiZ, tray, hotkeys y suspensión siguen requiriendo la checklist
manual porque dependen del escritorio y la red reales.

## Build desde GitHub Actions

El workflow `Build Windows` se dispara automáticamente al subir una rama
`release/**` y al publicar un tag `v*`. Cuando ya existe en la rama por defecto,
también puede ejecutarse desde **Actions → Build Windows → Run workflow**.

El resultado aparece como artifact:

```text
WizZDesktop-windows-x64
```

## Datos persistentes

En `python main.py`, WizZ conserva `config/json` para facilitar desarrollo.

En el ejecutable, Flet define `FLET_APP_STORAGE_DATA`; WizZ guarda allí:

```text
config/*.json
logs/wizz.log
```

La ubicación exacta puede abrirse desde **Ajustes → Acerca de → Datos/Logs**.
Los datos se conservan entre actualizaciones de la aplicación.

En el primer arranque empaquetado, si se ejecuta desde el repositorio y el
storage nuevo está vacío, WizZ intenta migrar los JSON de desarrollo sin
sobrescribir datos existentes.

## Checklist del release candidate

1. Abrir `WizZDesktop.exe` desde la carpeta completa.
2. Confirmar icono correcto en título, taskbar y bandeja.
3. Descubrir/controlar una ampolleta por LAN.
4. Probar color, Kelvin, brillo, escenas, favoritos y rutinas.
5. Probar hotkeys con la ventana visible, minimizada y oculta.
6. Ejecutar el EXE por segunda vez: debe restaurar la primera instancia.
7. Activar **Iniciar con Windows**, cerrar sesión o reiniciar y verificar.
8. Cerrar con X: debe ir a bandeja cuando la opción está activa.
9. Salir desde el menú tray y confirmar que no queda un proceso zombie.
10. Abrir **Ajustes → Datos/Logs** y revisar que los archivos sean persistentes.

## Diagnóstico

El log persistente está en la carpeta **Logs** mostrada en Ajustes. Flet también
puede generar `console.log` en su storage temporal de producción.

Antes de reportar un fallo, adjuntar:

- `wizz.log`;
- versión y build mostrados en Ajustes;
- si ocurrió en build local o artifact de Actions;
- pasos exactos para reproducirlo.
