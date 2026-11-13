$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
$spec = Join-Path $PSScriptRoot 'CrossHair.spec'
$installerScript = Join-Path $PSScriptRoot 'AkrosCrossHair.iss'
$appIcon = Join-Path $projectRoot 'assets\akros_crosshair.ico'
$appLicense = Join-Path $projectRoot 'LICENSE'
$appNotice = Join-Path $projectRoot 'NOTICE'
$outputDir = Join-Path $projectRoot 'dist\installer'
$appDir = Join-Path $projectRoot 'build\installer\app-release'

$isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($isccCommand) {
    $iscc = $isccCommand.Source
} else {
    $isccCandidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    $iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $iscc) {
    throw 'Se requiere Inno Setup 6. Instálalo desde https://jrsoftware.org/isinfo.php y asegúrate de que ISCC.exe esté disponible.'
}

Push-Location $projectRoot
try {
    & $python -c 'import PyInstaller'
    if ($LASTEXITCODE -ne 0) {
        throw 'No se encontró PyInstaller. Instala las dependencias con: python -m pip install -r packaging\requirements-build.txt'
    }

    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath $appDir `
        --workpath (Join-Path $projectRoot 'build\pyinstaller') `
        $spec
    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller no pudo generar AkrosCrossHair.exe.'
    }

    & $iscc `
        "/DAppSourceDir=$appDir" `
        "/DOutputDir=$outputDir" `
        "/DAppIconFile=$appIcon" `
        "/DAppLicenseFile=$appLicense" `
        "/DAppNoticeFile=$appNotice" `
        $installerScript
    if ($LASTEXITCODE -ne 0) {
        throw 'Inno Setup no pudo generar el instalador de Windows.'
    }

    Write-Output "Instalador de Windows creado: $(Join-Path $outputDir 'AkrosCrossHair-Setup.exe')"
}
finally {
    Pop-Location
}
