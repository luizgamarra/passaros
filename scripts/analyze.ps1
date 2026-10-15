param([string]$Audio='data/example_blackbird.wav')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Cache = Join-Path $env:USERPROFILE 'birdnet-build\analyzer-cache'
if (!(Test-Path -LiteralPath $Cache)) {
    New-Item -ItemType Directory -Force $Cache | Out-Null
    $Downloaded = Join-Path $Root 'models\analyzer'
    if (Test-Path -LiteralPath $Downloaded) { Copy-Item -Path "$Downloaded\*" -Destination $Cache -Recurse -Force }
}
# TensorFlow's Windows model loader cannot open the accented workspace path.
$env:BIRDNET_APP_DATA = $Cache
$env:TF_ENABLE_ONEDNN_OPTS = '0'
Push-Location $Root
try {
    & "$Root\.venv\Scripts\python.exe" -m birdnet_analyzer.analyze $Audio --birdnet 2.4 -o results/analyzer --rtype csv --min_conf 0.25 --n_workers 1 -l pt
    if ($LASTEXITCODE) { throw "Analise falhou: $LASTEXITCODE" }
} finally { Pop-Location }
