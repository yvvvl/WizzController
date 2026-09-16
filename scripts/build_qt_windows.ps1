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
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = (Get-Command python -ErrorAction Stop).Source }

$Version = ((& $Python -c "from app_meta import APP_VERSION; print(APP_VERSION)") | Out-String).Trim()
$BuildNumber = ((& $Python -c "from app_meta import APP_BUILD_NUMBER; print(APP_BUILD_NUMBER)") | Out-String).Trim()
$Artifact = ((& $Python -c "from app_meta import APP_ARTIFACT; print(APP_ARTIFACT)") | Out-String).Trim()
$Product = ((& $Python -c "from app_meta import APP_PRODUCT; print(APP_PRODUCT)") | Out-String).Trim()
$ResolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputDir)) { [System.IO.Path]::GetFullPath($OutputDir) } else { [System.IO.Path]::GetFullPath((Join-Path $Root $OutputDir)) }
$BuildWork = Join-Path $Root "build\pyinstaller"

if (-not $SkipInstall) {
    & $Python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}
if (-not $SkipTests) {
    & $Python -m compileall -q app_meta.py core config qt_ui tests tools
    if ($LASTEXITCODE -ne 0) { throw "compileall failed." }
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; build cancelled." }
}

if ($Clean) {
    Remove-Item $ResolvedOutput -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $BuildWork -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $ResolvedOutput, $BuildWork | Out-Null

$PyInstallerArgs = @(
    "--noconfirm", "--clean", "--windowed",
    "--name", $Artifact,
    "--distpath", $ResolvedOutput,
    "--workpath", $BuildWork,
    "--specpath", $BuildWork,
    "--add-data", "$Root\assets;assets",
    "--add-data", "$Root\qt_ui\qml;qt_ui\qml",
    "--collect-data", "PySide6",
    "--collect-binaries", "PySide6",
    "--collect-data", "certifi",
    "--hidden-import", "PySide6.QtQuickControls2",
    "--hidden-import", "PySide6.QtWidgets",
    "$Root\qt_ui\run.py"
)
& $Python -m PyInstaller @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$PackageDir = Join-Path $ResolvedOutput $Artifact
$Exe = Join-Path $PackageDir "$Artifact.exe"
if (-not (Test-Path $Exe)) { throw "Build completed without $Artifact.exe" }

$Manifest = [ordered]@{
    product = $Product; version = $Version; build_number = [int]$BuildNumber
    artifact = $Artifact; architecture = "x64"; packaging = "PyInstaller Qt"
    built_at_utc = [DateTime]::UtcNow.ToString("o")
}
$Manifest | ConvertTo-Json -Depth 3 | Set-Content -Path (Join-Path $PackageDir "BUILD_INFO.json") -Encoding utf8

$ReleaseDir = Join-Path $Root "dist\release"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
$ZipName = "$Artifact-v$Version-windows-x64.zip"
$ZipPath = Join-Path $ReleaseDir $ZipName
$HashPath = "$ZipPath.sha256"
Remove-Item $ZipPath, $HashPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal
$Hash = (Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $ZipName" | Set-Content -Path $HashPath -Encoding ascii

Write-Host "Qt beta build ready:" -ForegroundColor Green
Write-Host "  EXE : $Exe"
Write-Host "  ZIP : $ZipPath"
Write-Host "  SHA : $HashPath"
