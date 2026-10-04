$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $PyLauncher) {
    & py -3.13 .\run_validation.py
    exit $LASTEXITCODE
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($null -ne $Python) {
    & python .\run_validation.py
    exit $LASTEXITCODE
}

Write-Error "Python bulunamadı. windows/README.md içindeki ilk adımı çalıştırın."

