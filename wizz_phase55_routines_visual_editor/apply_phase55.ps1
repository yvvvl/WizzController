param(
    [Parameter(Mandatory=$true)]
    [string]$Repo
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path $Repo
$src = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[Phase55] Repo: $root"

$files = @(
    "ui\components\routines_panel.py",
    "ui\scene_visuals.py",
    "core\action_sequence.py",
    "pytest.ini"
)

foreach ($rel in $files) {
    $from = Join-Path $src $rel
    $to = Join-Path $root $rel
    $dir = Split-Path -Parent $to
    if (!(Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Copy-Item $from $to -Force
    Write-Host "[Phase55] Copiado: $rel"
}

Push-Location $root
try {
    python -m compileall -q main.py core config ui tests tools
    Write-Host "[Phase55] compileall OK"

    python -c "import pytest" 2>$null
    if ($LASTEXITCODE -eq 0) {
        pytest -q
        if ($LASTEXITCODE -ne 0) { throw "pytest falló" }
        Write-Host "[Phase55] pytest OK"
    } else {
        Write-Host "[Phase55] pytest no disponible; saltando tests." -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}

Write-Host "[Phase55] Listo. Ejecuta: python main.py"
