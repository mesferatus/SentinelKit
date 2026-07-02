param(
    [switch]$Browser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Ambiente Python não encontrado em .venv. Crie-o e instale api\requirements.txt."
}

$env:DATABASE_URL = "sqlite+pysqlite:///$((Join-Path $env:LOCALAPPDATA 'SentinelKit\sentinelkit.db').Replace('\', '/'))"
$env:CELERY_TASK_ALWAYS_EAGER = "true"
$env:API_HOST = "127.0.0.1"
$env:API_PORT = "8000"
$env:CORS_ORIGINS = '["http://127.0.0.1:5173","http://localhost:5173"]'
$env:ALLOWED_SCAN_TARGETS = '["localhost","127.0.0.1","::1"]'

if ($Browser) {
    $backend = Start-Process -FilePath $python -ArgumentList "-m", "app.desktop" -WorkingDirectory (Join-Path $root "api") -WindowStyle Hidden -PassThru
    try {
        & npm.cmd run dev --prefix (Join-Path $root "frontend")
    }
    finally {
        Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    }
    return
}

& npm.cmd run build --prefix (Join-Path $root "frontend")
& npm.cmd run desktop:dev --prefix (Join-Path $root "frontend")
