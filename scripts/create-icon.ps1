$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$source = Join-Path $root "frontend\src\assets\sentinelkit-mark.svg"
$outputDirectory = Join-Path $root "frontend\build"
$output = Join-Path $outputDirectory "icon.ico"

if (-not (Test-Path $source)) {
    throw "Identidade oficial não encontrada em $source."
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
& $python -c @"
from PIL import Image, ImageDraw
from pathlib import Path

source = Path(r'$source')
output = Path(r'$output')
if '<svg' not in source.read_text(encoding='utf-8'):
    raise SystemExit('Fonte SVG oficial inválida.')

scale = 8
image = Image.new('RGBA', (128 * scale, 128 * scale), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
scaled = lambda points: [(x * scale, y * scale) for x, y in points]

teal = '#119fbe'
shield = scaled([(64,12),(105,27),(105,58),(102,73),(95,88),(83,103),(64,119),(45,107),(33,92),(25,76),(23,58),(23,27)])
draw.line(shield + [shield[0]], fill=teal, width=9*scale, joint='curve')
draw.ellipse((51*scale,44*scale,77*scale,70*scale), fill=teal)
draw.rounded_rectangle((59*scale,63*scale,69*scale,91*scale), radius=5*scale, fill=teal)

image = image.resize((256, 256), Image.Resampling.LANCZOS)
image.save(output, sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
"@
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível criar o ícone oficial. Verifique o Pillow."
}
