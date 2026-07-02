$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Ambiente Python não encontrado em .venv."
}

Push-Location (Join-Path $root "api")
try {
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --name sentinelkit-api `
        --collect-all uvicorn `
        --collect-all celery `
        --collect-all passlib `
        --hidden-import app.models `
        --hidden-import app.tasks `
        --add-data "alembic;alembic" `
        --add-data "alembic.ini;." `
        --paths . `
        app\desktop.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou com código $LASTEXITCODE." }
}
finally {
    Pop-Location
}
