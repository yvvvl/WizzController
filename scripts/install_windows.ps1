[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "WizZDesktop"),
    [switch]$NoShortcuts,
    [switch]$Start
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$archivePath = [System.IO.Path]::GetFullPath($Archive)
if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) { throw "Release ZIP was not found: $archivePath" }
if ([System.IO.Path]::GetExtension($archivePath) -ne ".zip") { throw "The installer requires the WizZ Desktop .zip release asset." }

$target = [System.IO.Path]::GetFullPath($InstallDir)
$parent = Split-Path -Parent $target
$stage = Join-Path $parent (".WizZDesktop-stage-" + [guid]::NewGuid().ToString("N"))
$backup = "$target.backup"
New-Item -ItemType Directory -Force -Path $parent | Out-Null
try {
    Expand-Archive -LiteralPath $archivePath -DestinationPath $stage -Force
    $exe = Join-Path $stage "WizZDesktop.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "The ZIP does not contain WizZDesktop.exe at its root." }
    if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Recurse -Force }
    if (Test-Path -LiteralPath $target) { Move-Item -LiteralPath $target -Destination $backup }
    try { Move-Item -LiteralPath $stage -Destination $target }
    catch { if (Test-Path -LiteralPath $backup) { Move-Item -LiteralPath $backup -Destination $target }; throw }
    Remove-Item -LiteralPath $backup -Recurse -Force -ErrorAction SilentlyContinue
    if (-not $NoShortcuts) {
        $shell = New-Object -ComObject WScript.Shell
        $desktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "WizZ Desktop.lnk"
        $menuFolder = Join-Path ([Environment]::GetFolderPath("Programs")) "WizZ Desktop"
        New-Item -ItemType Directory -Force -Path $menuFolder | Out-Null
        foreach ($linkPath in @($desktopLink, (Join-Path $menuFolder "WizZ Desktop.lnk"))) {
            $shortcut = $shell.CreateShortcut($linkPath)
            $shortcut.TargetPath = (Join-Path $target "WizZDesktop.exe")
            $shortcut.WorkingDirectory = $target
            $shortcut.IconLocation = (Join-Path $target "assets\icon_windows.ico")
            $shortcut.Save()
        }
    }
    Write-Host "WizZ Desktop installed in: $target" -ForegroundColor Green
    if ($Start) { Start-Process -FilePath (Join-Path $target "WizZDesktop.exe") -WorkingDirectory $target }
} finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue }
}
