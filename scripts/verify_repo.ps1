Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

python -m compileall .
python -m pytest -q
