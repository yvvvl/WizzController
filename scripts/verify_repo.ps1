Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { (Get-Command python -ErrorAction Stop).Source }

Push-Location $Root
try {
    & $Python -m compileall -q main.py app_meta.py core config qt_ui tests tools
    if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }
    & $Python tools/repository_hygiene.py
    if ($LASTEXITCODE -ne 0) { throw "Repository hygiene check failed." }
    & $Python -m ruff check . --select E9,F63,F7,F82
    if ($LASTEXITCODE -ne 0) { throw "Critical Python lint check failed." }
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
} finally {
    Pop-Location
}
