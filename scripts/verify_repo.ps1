Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

python -m compileall -q main.py app_meta.py core config ui tests tools
python -m pytest -q
