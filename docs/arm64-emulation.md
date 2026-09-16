# Emular la beta Linux ARM64

La beta ARM64 se construye de forma nativa en CI con un ejecutor Linux ARM64.
En un equipo Windows x64 también se puede emular Ubuntu ARM64 para revisar el
entorno, ejecutar comprobaciones de empaquetado y probar el arranque de la
aplicación.

La emulación no sustituye una prueba final en hardware ARM. Qt Quick depende
del controlador gráfico y del compositor de escritorio: la respuesta visual,
el color picker y las animaciones deben confirmarse al menos una vez en un
equipo ARM64 real antes de publicar una beta.

## Comprobación rápida desde Windows

Instala Docker Desktop con el motor WSL 2 y contenedores Linux. Con Docker en
ejecución, abre PowerShell en el repositorio y ejecuta:

```powershell
docker run --rm --platform linux/arm64 ubuntu:24.04 uname -m
```

La salida esperada es `aarch64`. Eso confirma que Docker puede ejecutar una
imagen Ubuntu ARM64 bajo emulación.

## Qué validar con la emulación

- Que el paquete `linux-arm64` se extrae correctamente.
- Que `BUILD_INFO.json` declara `"architecture": "arm64"`.
- Las pruebas Python y los flujos sin interfaz que no dependan de GPU.
- El inicio básico de la aplicación en una sesión gráfica ARM64 cuando el
  contenedor tenga un servidor gráfico disponible.

Para crear el artefacto definitivo, usa el flujo **Linux beta build** de
GitHub Actions. Selecciona el resultado `linux-arm64`; se compila en el
ejecutor ARM64, no mediante compilación cruzada desde x64.

## Prueba en un equipo ARM64 real

En Ubuntu ARM64, instala las dependencias de desarrollo, crea el entorno
Python y ejecuta la compilación nativa:

```bash
bash scripts/build_linux.sh --arch arm64
```

El script rechaza intencionalmente una arquitectura distinta a la del sistema.
Así se evita publicar un archivo con bibliotecas nativas de la CPU equivocada.
