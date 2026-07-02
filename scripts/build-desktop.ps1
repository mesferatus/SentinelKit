$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

& (Join-Path $PSScriptRoot "build-backend.ps1")
if ($LASTEXITCODE -ne 0) { throw "Build do backend falhou." }

Push-Location (Join-Path $root "frontend")
try {
    & npm.cmd run desktop:build
    if ($LASTEXITCODE -ne 0) { throw "Build Electron falhou com código $LASTEXITCODE." }
}
finally {
    Pop-Location
}

Write-Host "Artefatos gerados em: $(Join-Path $root 'release')"
