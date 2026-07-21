# Flujo Git recomendado para cerrar la v1

No conviene seguir acumulando cambios grandes sin checkpoints. Desde esta etapa,
cada bloque debe quedar en un commit pequeño, probado y reversible.

## 1. Revisar conexión con GitHub

```powershell
git remote -v
git branch --show-current
git status
```

Si no existe `origin`:

```powershell
git remote add origin https://github.com/yvvvl/WizzController.git
```

Si existe con otra URL:

```powershell
git remote set-url origin https://github.com/yvvvl/WizzController.git
```

Luego:

```powershell
git fetch origin
```

No uses `git pull --rebase` ni `push --force` hasta comprobar si la historia
local y `origin/main` comparten base.

## 2. Crear rama de release

Con el proyecto funcionando y el working tree actual revisado:

```powershell
git switch -c release/v1.0.0
git status
```

El `main` público todavía puede estar detrás de tu carpeta local. Si los cambios
anteriores —sin voz, Color Studio, responsive, hotkeys/tray e instancia única—
todavía no tienen commit, crea un checkpoint único y honesto en lugar de
inventar historia retroactiva:

```powershell
git add -A
git commit -m "feat: prepare WizZ Desktop v1 release candidate"
```

Desde ese punto, usar commits separados.

## 3. Commits de esta fase

Orden recomendado para los cambios de packaging:

```text
fix: persist packaged config and resolve Windows startup launcher
feat: add v1 branding, version metadata and tray icon
build: add Flet Windows build pipeline and GitHub artifact
docs: document Windows build and release workflow
```

Los patches entregados con esta fase están ordenados con esos mensajes y se
pueden aplicar con `git am` sobre la versión RC anterior, siempre con working
tree limpio. Si ya copiaste la carpeta final completa, usa staging selectivo en
vez de aplicar los patches otra vez.

Antes de cada commit:

```powershell
python -m compileall -q main.py app_meta.py core config ui tests tools
python -m pytest -q
git diff --check
git status
```

Ejemplo de staging selectivo:

```powershell
git add app_meta.py config/paths.py config/base_manager.py `
  config/config_manager.py config/app_runtime_manager.py `
  core/logging_setup.py core/windows_window.py main.py tests/
git commit -m "fix: persist packaged config and resolve Windows startup launcher"
```

Nunca usar `git add .` por reflejo antes de revisar `git status`; los JSON reales
pueden contener IP, MAC y hotkeys.

## 4. Subir la rama

```powershell
git push -u origin release/v1.0.0
```

El push a `release/**` dispara tanto CI como la build Windows. Después se abre
un Pull Request hacia `main`; ambos workflows deben quedar verdes y el artifact
debe pasar el smoke test antes de fusionar.

## 5. Tag de la versión inicial

Tras aprobar el release candidate y fusionar:

```powershell
git switch main
git pull --ff-only origin main
git tag -a v1.0.0 -m "WizZ Desktop v1.0.0"
git push origin v1.0.0
```

El tag dispara el workflow de Windows. Descarga el artifact, repite el smoke test
y recién entonces publícalo como release.

## Recuperación segura

Antes de cualquier operación delicada:

```powershell
git branch backup/pre-v1-$(Get-Date -Format yyyyMMdd-HHmm)
git status
```

Evitar:

```text
git reset --hard
git clean -fd
git push --force
```

salvo que exista un backup verificado y se entienda exactamente qué se perderá.
