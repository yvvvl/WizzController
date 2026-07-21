[CmdletBinding()]
param(
    [string]$BuildDirectory = "dist\windows",
    [int]$WaitSeconds = 7,
    [switch]$LaunchSecondInstance
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ([System.IO.Path]::IsPathRooted($BuildDirectory)) {
    $BuildPath = [System.IO.Path]::GetFullPath($BuildDirectory)
} else {
    $BuildPath = [System.IO.Path]::GetFullPath(
        (Join-Path $Root $BuildDirectory)
    )
}

if (-not (Test-Path $BuildPath)) {
    throw "No existe la carpeta de build: $BuildPath"
}

$Exe = Get-ChildItem `
    -Path $BuildPath `
    -Filter "WizZDesktop.exe" `
    -File `
    -Recurse |
    Select-Object -First 1

if ($null -eq $Exe) {
    throw "No se encontro WizZDesktop.exe en $BuildPath."
}

function Get-WizzOwnerProcess {
    $OwnerFile = Join-Path $env:TEMP "WizZDesktop.lock.owner.json"

    if (-not (Test-Path $OwnerFile)) {
        return $null
    }

    try {
        $Payload = Get-Content $OwnerFile -Raw | ConvertFrom-Json
        $OwnerPid = [int]$Payload.pid

        if ($OwnerPid -le 0) {
            return $null
        }

        return Get-Process -Id $OwnerPid -ErrorAction Stop
    } catch {
        return $null
    }
}

function Get-SafeProcessPath {
    param(
        [System.Diagnostics.Process]$Process
    )

    try {
        $Process.Refresh()
        return $Process.Path
    } catch {
        return $null
    }
}

$ExpectedExe = [System.IO.Path]::GetFullPath($Exe.FullName)
$Primary = Get-WizzOwnerProcess

if ($null -ne $Primary) {
    $OwnerPath = Get-SafeProcessPath $Primary

    if (
        -not $OwnerPath -or
        -not [string]::Equals(
            [System.IO.Path]::GetFullPath($OwnerPath),
            $ExpectedExe,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw (
            "Hay otra instancia de WizZ activa, posiblemente python main.py. " +
            "Cierrala desde el tray antes de probar el EXE."
        )
    }

    Write-Host (
        "Usando instancia existente de WizZ Desktop " +
        "(PID $($Primary.Id))."
    ) -ForegroundColor Yellow
} else {
    Write-Host "Abriendo $ExpectedExe" -ForegroundColor Cyan

    $Launcher = Start-Process `
        -FilePath $ExpectedExe `
        -WorkingDirectory $Exe.DirectoryName `
        -PassThru

    Start-Sleep -Seconds $WaitSeconds
    $Launcher.Refresh()

    if ($Launcher.HasExited) {
        $OwnerAfterLaunch = Get-WizzOwnerProcess

        if (
            $Launcher.ExitCode -eq 0 -and
            $null -ne $OwnerAfterLaunch
        ) {
            $Primary = $OwnerAfterLaunch
        } else {
            throw (
                "WizZ Desktop termino durante el arranque con codigo " +
                "$($Launcher.ExitCode)."
            )
        }
    } else {
        $Primary = $Launcher
    }

    Write-Host (
        "Primera instancia activa (PID $($Primary.Id))."
    ) -ForegroundColor Green
}

$Primary.Refresh()

if ($Primary.HasExited) {
    throw "La instancia principal dejo de ejecutarse."
}

if ($LaunchSecondInstance) {
    Write-Host (
        "Abriendo una segunda instancia para validar restauracion..."
    ) -ForegroundColor Cyan

    $Second = Start-Process `
        -FilePath $ExpectedExe `
        -WorkingDirectory $Exe.DirectoryName `
        -PassThru

    if (-not $Second.WaitForExit(10000)) {
        Stop-Process -Id $Second.Id -Force -ErrorAction SilentlyContinue
        throw (
            "La segunda ejecucion no termino en 10 segundos. " +
            "Podria existir una instancia duplicada."
        )
    }

    if ($Second.ExitCode -ne 0) {
        throw (
            "La segunda ejecucion termino con codigo " +
            "$($Second.ExitCode)."
        )
    }

    Start-Sleep -Seconds 1
    $Primary.Refresh()

    if ($Primary.HasExited) {
        throw "La instancia principal termino durante la prueba."
    }

    Write-Host (
        "Instancia unica validada: la segunda ejecucion termino con " +
        "codigo 0 y la principal sigue activa."
    ) -ForegroundColor Green
}

Write-Host ""
Write-Host "Checklist manual de release candidate:" -ForegroundColor Yellow
Write-Host "  1. Icono correcto en ventana, taskbar y bandeja"
Write-Host "  2. Control LAN: encendido, brillo, RGB, Kelvin y escenas"
Write-Host "  3. Hotkeys con ventana visible, minimizada y oculta"
Write-Host "  4. La X oculta la app y Mostrar WizZ la restaura"
Write-Host "  5. Una segunda ejecucion restaura la primera"
Write-Host "  6. Inicio con Windows apunta a WizZDesktop.exe"
Write-Host "  7. Tray > Salir no deja procesos vivos"
Write-Host "  8. Ajustes > Datos y Logs abre el storage persistente"
