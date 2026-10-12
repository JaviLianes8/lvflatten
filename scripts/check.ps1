# Local quality gate. Run before every commit. No CI runs in the cloud.
# Each gate must exit 0 on its own.
$ErrorActionPreference = "Stop"

function Invoke-Gate([string]$Command) {
    Write-Host "> $Command"
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) { throw "gate failed: $Command" }
}

Invoke-Gate "ruff format --check ."
Invoke-Gate "ruff check ."
Invoke-Gate "mypy --strict src"
Invoke-Gate "mypy --strict src tests"
Invoke-Gate "python -m pytest"
