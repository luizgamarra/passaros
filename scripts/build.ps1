param([ValidateSet('build','menuconfig','flash','monitor')][string]$Action='build', [string]$Port,
      [string]$FirmwareDir='', [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$BuildName='passaros',
      [string]$ArtifactsDir='')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Stage = Join-Path $env:USERPROFILE "birdnet-build\$BuildName"
$Idf = 'C:\Espressif\frameworks\esp-idf-v5.5.2'
if (!$FirmwareDir) { $FirmwareDir = Join-Path $Root 'firmware' }
$FirmwareDir = (Resolve-Path -LiteralPath $FirmwareDir).Path
if ($FirmwareDir -ne (Join-Path $Root 'firmware') -and $BuildName -eq 'passaros') { throw 'Use -BuildName exclusivo para o firmware customizado.' }
if (!$ArtifactsDir) { $ArtifactsDir = Join-Path $Root 'artifacts' }
if (![System.IO.Path]::IsPathRooted($ArtifactsDir)) { $ArtifactsDir = Join-Path $Root $ArtifactsDir }
if (!(Test-Path -LiteralPath "$FirmwareDir\main\model.tflite")) { throw 'Prepare o modelo e os vetores do firmware primeiro.' }
if ($Action -in 'flash','monitor' -and $Port -notmatch '^COM[1-9][0-9]*$') { throw 'Informe -Port COMx da placa real.' }
if (!(Test-Path -LiteralPath "$Idf\export.ps1")) { throw "ESP-IDF ausente: $Idf" }
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
Copy-Item -Path "$FirmwareDir\*" -Destination $Stage -Recurse -Force
$env:IDF_TOOLS_PATH = 'C:\Espressif'
. "$Idf\export.ps1"
Push-Location $Stage
try {
    if (!(Test-Path -LiteralPath 'sdkconfig')) { idf.py set-target esp32s3; if ($LASTEXITCODE) { throw 'set-target falhou' } }
    if ($Action -in 'flash','monitor') { idf.py -p $Port $Action }
    else { idf.py $Action }
    if ($LASTEXITCODE) { throw "ESP-IDF $Action falhou: $LASTEXITCODE" }
    if ($Action -eq 'build') {
        $Artifacts = $ArtifactsDir
        New-Item -ItemType Directory -Force $Artifacts | Out-Null
        Copy-Item build/passaros_tiny.bin,build/passaros_tiny.elf,build/flasher_args.json -Destination $Artifacts -Force
        Copy-Item build/bootloader/bootloader.bin,build/partition_table/partition-table.bin -Destination $Artifacts -Force
        Copy-Item sdkconfig,dependencies.lock -Destination $Artifacts -Force
        & "$Root\.venv\Scripts\python.exe" "$Root\scripts\export_artifacts.py" $Artifacts
        if ($LASTEXITCODE) { throw 'Exportacao do firmware falhou' }
    }
} finally { Pop-Location }
