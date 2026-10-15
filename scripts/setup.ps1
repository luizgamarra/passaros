$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (!(Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git ausente no PATH.' }
    if (!(Get-Command uv -ErrorAction SilentlyContinue)) { throw 'uv ausente no PATH.' }
    git submodule update --init
    if ($LASTEXITCODE) { throw 'Download das dependencias upstream falhou' }
    New-Item -ItemType Directory -Force -Path 'results','models','data' | Out-Null
    if (!(Test-Path '.venv\Scripts\python.exe')) {
        uv venv --python 3.11 .venv
        if ($LASTEXITCODE) { throw 'Criacao do ambiente falhou' }
    }
    uv pip install --python .venv/Scripts/python.exe -r requirements.lock.txt
    if ($LASTEXITCODE) { throw 'Instalacao das dependencias falhou' }
    uv pip install --python .venv/Scripts/python.exe --no-deps -e upstream/BirdNET-Analyzer
    if ($LASTEXITCODE) { throw 'Instalacao do Analyzer falhou' }
    & .venv/Scripts/python.exe scripts/prepare_example.py
    if ($LASTEXITCODE) { throw 'Geracao do exemplo falhou' }
} finally { Pop-Location }
