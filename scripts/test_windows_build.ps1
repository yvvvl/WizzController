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
    $BuildPath = [System.IO.Path]::GetFullPath((Join-Path $Root $BuildDirectory))
}

$Exe = Get-ChildItem -Path $BuildPath -Filter "WizZDesktop.exe" -File -Recurse | Select-Object -First 1
if ($null -eq $Exe) {
    throw "No se encontró WizZDesktop.exe en $BuildPath. Ejecuta primero scripts\build_windows.ps1."
}

Write-Host "Abriendo $($Exe.FullName)" -ForegroundColor Cyan
$Process = Start-Process -FilePath $Exe.FullName -WorkingDirectory $Exe.DirectoryName -PassThru
Start-Sleep -Seconds $WaitSeconds

$Process.Refresh()
if ($Process.HasExited) {
    throw "El launcher terminó durante el arranque con código $($Process.ExitCode). Abre Ajustes → Logs o busca wizz.log en el storage de Flet."
}

Write-Host "Primer launcher activo (PID $($Process.Id))." -ForegroundColor Green

if ($LaunchSecondInstance) {
    Write-Host "Abriendo una segunda instancia para validar restauración..." -ForegroundColor Cyan
    $Second = Start-Process -FilePath $Exe.FullName -WorkingDirectory $Exe.DirectoryName -PassThru
    if (-not $Second.WaitForExit(10000)) {
        Write-Warning "La segunda ejecución no terminó en 10 s. Revisa si apareció una segunda ventana o tray."
    } else {
        Write-Host "La segunda ejecución terminó con código $($Second.ExitCode). La primera ventana debe haberse restaurado." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Checklist manual de release candidate:" -ForegroundColor Yellow
Write-Host "  1. icono correcto en ventana, taskbar y bandeja"
Write-Host "  2. control LAN: encendido, brillo, RGB, Kelvin y escenas"
Write-Host "  3. hotkeys con la ventana visible, minimizada y oculta"
Write-Host "  4. X → bandeja y Mostrar WizZ"
Write-Host "  5. ejecutar el EXE dos veces: restaura la primera instancia"
Write-Host "  6. Inicio con Windows apunta a WizZDesktop.exe"
Write-Host "  7. Tray → Salir no deja procesos vivos"
Write-Host "  8. Ajustes → Datos/Logs abre el storage persistente"
