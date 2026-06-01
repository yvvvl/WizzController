# WizZ Controller

App de escritorio en **Python + Flet** para controlar ampolletas WiZ por LAN.

## Funciones principales

- Control WiZ local por UDP (`setPilot`, `getPilot`, `getSystemConfig`).
- Discovery híbrido: UDP local + pywizlight como apoyo.
- Modo **una ampolleta** o **todas**.
- Sincronización de estado: si cambias la luz desde el celular, la app actualiza la UI.
- Paneles: Inicio, Color, Escenas, Favoritos, Rutinas, Ajustes, Hotkeys y Voz.
- Voz local/offline con `faster-whisper`, activadores configurables y perfil adaptativo de micrófono.
- Rutinas compuestas sin programación por hora.
- Hotkeys globales y bandeja del sistema.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scriptsctivate
python -m pip install -r requirements.txt
python main.py
```

## Voz

Activadores recomendados:

```txt
pc, pese, wizz, wiz
```

Ejemplos:

```txt
pc apaga la luz
pese prende la luz al cincuenta
wizz pon rojo al cien
wiz modo cine
```

## Configuración local

Los archivos reales de `config/json/*.json` se crean automáticamente al ejecutar la app y **no se versionan** porque pueden contener IP, MAC, hotkeys y perfil vocal.

En `config/json/*.example.json` hay ejemplos seguros para referencia.

## Verificación rápida

```powershell
python -m compileall .
python -m pytest
```

## Estructura

```txt
core/       lógica WiZ, voz, rutinas y bandeja
config/     managers JSON
ui/         paneles Flet
assets/     recursos visuales
tools/      utilidades de diagnóstico
tests/      pruebas mínimas
```
