[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipInstall,
    [switch]$SkipTests,
    [string]$OutputDir = "dist/windows"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:FLET_CLI_NO_RICH_OUTPUT = "true"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

if ($env:OS -ne "Windows_NT") {
    throw "This build must run on Windows."
}

function Find-VisualStudioInstall {
    param([string]$VsWhere)

    if (-not (Test-Path $VsWhere)) {
        return $null
    }

    $value = ((
        & $VsWhere `
            -latest `
            -products "*" `
            -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
            -property installationPath
    ) | Out-String).Trim()

    return $value
}

function Find-VcRuntimeFile {
    param(
        [string]$VisualStudioInstall,
        [string]$FileName
    )

    if (-not $VisualStudioInstall) {
        return $null
    }

    $redistRoot = Join-Path $VisualStudioInstall "VC\Redist\MSVC"
    if (-not (Test-Path $redistRoot)) {
        return $null
    }

    $escapedName = [Regex]::Escape($FileName)
    $runtimeFile = Get-ChildItem `
        -Path $redistRoot `
        -Recurse `
        -File `
        -Filter $FileName `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -match "\\x64\\Microsoft\.VC\d+\.CRT\\$escapedName$"
        } |
        Sort-Object FullName -Descending |
        Select-Object -First 1

    return $runtimeFile
}

function Repair-FletWindowsInstall {
    param(
        [string]$ProjectRoot,
        [string]$ResolvedOutput,
        [string]$Artifact,
        [string]$VisualStudioInstall
    )

    $buildDir = Join-Path $ProjectRoot "build\flutter\build\windows\x64"
    $installScript = Join-Path $buildDir "cmake_install.cmake"
    $runnerRelease = Join-Path $buildDir "runner\Release"
    $builtExe = Join-Path $runnerRelease "$Artifact.exe"

    if (
        -not (Test-Path $installScript) -or
        -not (Test-Path $builtExe) -or
        -not $VisualStudioInstall
    ) {
        return $false
    }

    $installText = [System.IO.File]::ReadAllText($installScript)
    $changed = $false

    foreach ($runtimeName in @(
        "msvcp140.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll"
    )) {
        $runtimeFile = Find-VcRuntimeFile `
            -VisualStudioInstall $VisualStudioInstall `
            -FileName $runtimeName

        if ($null -eq $runtimeFile) {
            continue
        }

        $systemPath = "C:/Windows/System32/$runtimeName"
        if (-not $installText.Contains($systemPath)) {
            continue
        }

        $redistPath = $runtimeFile.FullName.Replace("\", "/")
        $installText = $installText.Replace($systemPath, $redistPath)
        $changed = $true
    }

    if (-not $changed) {
        return $false
    }

    [System.IO.File]::WriteAllText(
        $installScript,
        $installText,
        [System.Text.UTF8Encoding]::new($false)
    )

    $cmake = Join-Path `
        $VisualStudioInstall `
        "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"

    if (-not (Test-Path $cmake)) {
        $cmakeCommand = Get-Command cmake -ErrorAction SilentlyContinue
        if ($null -eq $cmakeCommand) {
            return $false
        }
        $cmake = $cmakeCommand.Source
    }

    Write-Warning (
        "Flet compiled the app but CMake could not install a VC runtime. " +
        "Retrying with the x64 Visual Studio redist files."
    )

    $cmakeExitCode = 1
    Push-Location $buildDir
    try {
        & $cmake "-DBUILD_TYPE=Release" "-P" ".\cmake_install.cmake"
        $cmakeExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($cmakeExitCode -ne 0 -or -not (Test-Path $builtExe)) {
        return $false
    }

    Remove-Item $ResolvedOutput -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $ResolvedOutput | Out-Null
    Copy-Item `
        -Path (Join-Path $runnerRelease "*") `
        -Destination $ResolvedOutput `
        -Recurse `
        -Force

    return (Test-Path (Join-Path $ResolvedOutput "$Artifact.exe"))
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

if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    $ResolvedOutput = [System.IO.Path]::GetFullPath($OutputDir)
} else {
    $ResolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $Root $OutputDir))
}

Write-Host "== WizZ Desktop - Windows build ==" -ForegroundColor Cyan
Write-Host "Version: $Version (build $BuildNumber)"
Write-Host "Python : $PythonVersion - $Python"

$VsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$VsInstall = Find-VisualStudioInstall -VsWhere $VsWhere
if ($VsInstall) {
    Write-Host "Visual Studio C++: $VsInstall" -ForegroundColor DarkCyan
} elseif (Test-Path $VsWhere) {
    Write-Warning "Desktop development with C++ was not detected."
} else {
    Write-Warning "vswhere.exe is unavailable; Flutter will validate Visual Studio."
}

try {
    $DeveloperMode = Get-ItemPropertyValue `
        -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" `
        -Name "AllowDevelopmentWithoutDevLicense" `
        -ErrorAction Stop
    if ([int]$DeveloperMode -ne 1) {
        Write-Warning "Developer Mode is disabled; Flutter may need symlink support."
    }
} catch {
    Write-Warning "Developer Mode could not be checked."
}

if (-not $SkipInstall) {
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

    & $Python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}

if (-not $SkipTests) {
    & $Python -m compileall -q main.py app_meta.py core config ui tests tools
    if ($LASTEXITCODE -ne 0) { throw "compileall failed." }

    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; build cancelled." }
}

$Flet = Join-Path (Split-Path $Python) "flet.exe"
if (-not (Test-Path $Flet)) {
    $FletCommand = Get-Command flet -ErrorAction Stop
    $Flet = $FletCommand.Source
}
$FletVersion = ((& $Python -c "import flet; print(flet.__version__)") | Out-String).Trim()

if ($Clean) {
    Remove-Item (Join-Path $Root "build") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $ResolvedOutput -Recurse -Force -ErrorAction SilentlyContinue
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

Write-Host "Flet  : $FletVersion - $Flet" -ForegroundColor DarkCyan
Write-Host "Output: $ResolvedOutput" -ForegroundColor DarkCyan
& $Flet @BuildArgs
$FletExitCode = $LASTEXITCODE

$RecoveredRuntimeInstall = $false
if ($FletExitCode -ne 0) {
    $RecoveredRuntimeInstall = Repair-FletWindowsInstall `
        -ProjectRoot $Root `
        -ResolvedOutput $ResolvedOutput `
        -Artifact $Artifact `
        -VisualStudioInstall $VsInstall

    if (-not $RecoveredRuntimeInstall) {
        throw "flet build windows failed."
    }

    Write-Host "Recovered the Windows package after the VC runtime install error." -ForegroundColor Yellow
}

$Exe = Get-ChildItem -Path $ResolvedOutput -Filter "$Artifact.exe" -File -Recurse | Select-Object -First 1
if (-not $Exe) {
    throw "Build completed without finding $Artifact.exe in $ResolvedOutput"
}

$Commit = "no-git"
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
        $Commit = "no-git"
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
    runtime_install_recovered = [bool]$RecoveredRuntimeInstall
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
Write-Host "Build ready:" -ForegroundColor Green
Write-Host "  EXE : $($Exe.FullName)"
Write-Host "  INFO: $ManifestPath"
Write-Host "  ZIP : $ZipPath"
Write-Host "  SHA : $HashPath"
Write-Host ""
Write-Host "Distribute the complete ZIP; the EXE needs the bundled DLL and data files." -ForegroundColor Yellow
Write-Host "Smoke test: .\scripts\test_windows_build.ps1 -LaunchSecondInstance" -ForegroundColor Yellow
