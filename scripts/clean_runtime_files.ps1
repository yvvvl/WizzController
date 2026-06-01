Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Get-ChildItem -Recurse -Force -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Force -File -Include *.pyc,*.pyo,*.bak,*.backup | Remove-Item -Force
Remove-Item -Recurse -Force backups,.patch_backups -ErrorAction SilentlyContinue
