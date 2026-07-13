[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipInstall,
    [switch]$SkipTests,
    [string]$OutputDir = "dist/windows"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

if ($env:OS -ne "Windows_NT") {
    throw "Este build debe ejecutarse en Windows."
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $PythonCommand = Get-Command python -ErrorAction Stop
    $Python = $PythonCommand.Source
}

$Version = ((& $Python -c "from app_meta import APP_VERSION; print(APP_VERSION)") | Out-String).Trim()
$BuildNumber = ((& $Python -c "from app_meta import APP_BUILD_NUMBER; print(APP_BUILD_NUMBER)") | Out-String).Trim()
$Artifact = ((& $Python -c "from app_meta import APP_ARTIFACT; print(APP_ARTIFACT)") | Out-String).Trim()
$Product = ((& $Python -c "from app_meta import APP_PRODUCT; print(APP_PRODUCT)") | Out-String).Trim()
$PythonVersion = ((& $Python -c "import platform; print(platform.python_version())") | Out-String).Trim()

Write-Host "== WizZ Desktop · build Windows ==" -ForegroundColor Cyan
Write-Host "Versión: $Version (build $BuildNumber)"
Write-Host "Python : $PythonVersion · $Python"

# Flutter desktop para Windows requiere el toolchain C++ de Visual Studio.
$VsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $VsWhere) {
    $VsInstall = ((& $VsWhere -latest -products "*" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath) | Out-String).Trim()
    if ($VsInstall) {
        Write-Host "Visual Studio C++: $VsInstall" -ForegroundColor DarkCyan
    } else {
        Write-Warning "No se detectó Desktop development with C++. Flutter puede detener el build."
    }
} else {
    Write-Warning "vswhere.exe no está disponible; Flet/Flutter validará Visual Studio durante el build."
}

try {
    $DeveloperMode = Get-ItemPropertyValue `
        -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" `
        -Name "AllowDevelopmentWithoutDevLicense" `
        -ErrorAction Stop
    if ([int]$DeveloperMode -ne 1) {
        Write-Warning "Developer Mode no está activo. Habilítalo si Flutter informa que necesita symlinks."
    }
} catch {
    Write-Warning "No se pudo comprobar Developer Mode; se continuará."
}

if (-not $SkipInstall) {
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }

    & $Python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar dependencias." }
}

if (-not $SkipTests) {
    & $Python -m compileall -q main.py app_meta.py core config ui tests tools
    if ($LASTEXITCODE -ne 0) { throw "compileall falló." }

    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Los tests fallaron; se cancela el build." }
}

$Flet = Join-Path (Split-Path $Python) "flet.exe"
if (-not (Test-Path $Flet)) {
    $FletCommand = Get-Command flet -ErrorAction Stop
    $Flet = $FletCommand.Source
}
$FletVersion = ((& $Python -c "import flet; print(flet.__version__)") | Out-String).Trim()

if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    $ResolvedOutput = [System.IO.Path]::GetFullPath($OutputDir)
} else {
    $ResolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $Root $OutputDir))
}

$BuildArgs = @(
    "build",
    "windows",
    ".",
    "--output", $ResolvedOutput,
    "--yes",
    "--no-rich-output"
)
if ($Clean) {
    $BuildArgs += "--clear-cache"
}

Write-Host "Flet  : $FletVersion · $Flet" -ForegroundColor DarkCyan
Write-Host "Salida: $ResolvedOutput" -ForegroundColor DarkCyan
& $Flet @BuildArgs
if ($LASTEXITCODE -ne 0) { throw "flet build windows falló." }

$Exe = Get-ChildItem -Path $ResolvedOutput -Filter "$Artifact.exe" -File -Recurse | Select-Object -First 1
if (-not $Exe) {
    throw "Build completado sin encontrar $Artifact.exe en $ResolvedOutput"
}

$Commit = "sin-git"
$Dirty = $false
if (Test-Path (Join-Path $Root ".git")) {
    try {
        $CommitValue = ((& git "-C" $Root "rev-parse" "--short=12" "HEAD") | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $CommitValue) {
            $Commit = $CommitValue
        }
        $StatusValue = ((& git "-C" $Root "status" "--porcelain") | Out-String).Trim()
        if ($LASTEXITCODE -eq 0) {
            $Dirty = [bool]$StatusValue
        }
    } catch {
        $Commit = "sin-git"
        $Dirty = $false
    }
}

$Manifest = [ordered]@{
    product = $Product
    version = $Version
    build_number = [int]$BuildNumber
    artifact = $Artifact
    architecture = "x64"
    python = $PythonVersion
    flet = $FletVersion
    commit = $Commit
    dirty_worktree = $Dirty
    built_at_utc = [DateTime]::UtcNow.ToString("o")
}
$ManifestPath = Join-Path $ResolvedOutput "BUILD_INFO.json"
$Manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $ManifestPath -Encoding utf8

$ReleaseDir = Join-Path $Root "dist\release"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

$ZipName = "$Artifact-v$Version-windows-x64.zip"
$ZipPath = Join-Path $ReleaseDir $ZipName
$HashPath = "$ZipPath.sha256"
Remove-Item $ZipPath, $HashPath -Force -ErrorAction SilentlyContinue

Compress-Archive -Path (Join-Path $ResolvedOutput "*") -DestinationPath $ZipPath -CompressionLevel Optimal
$Hash = (Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $ZipName" | Set-Content -Path $HashPath -Encoding ascii

Write-Host ""
Write-Host "Build listo:" -ForegroundColor Green
Write-Host "  EXE : $($Exe.FullName)"
Write-Host "  INFO: $ManifestPath"
Write-Host "  ZIP : $ZipPath"
Write-Host "  SHA : $HashPath"
Write-Host ""
Write-Host "Distribuye el ZIP completo; el EXE necesita los DLL y archivos que Flet deja junto a él." -ForegroundColor Yellow
Write-Host "Smoke test: .\scripts\test_windows_build.ps1" -ForegroundColor Yellow
