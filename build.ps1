# Gera o executável em dist\YouTubeDownloader\ (com FFmpeg embutido)
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$vendorBin = Join-Path $root "vendor\ffmpeg\bin"
$ffmpegExe = Join-Path $vendorBin "ffmpeg.exe"
$ffprobeExe = Join-Path $vendorBin "ffprobe.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Criando ambiente virtual..."
    python -m venv (Join-Path $root ".venv")
}

Write-Host "Instalando dependencias de build..."
& $venvPython -m pip install -q -r (Join-Path $root "requirements.txt")
& $venvPython -m pip install -q -r (Join-Path $root "requirements-build.txt")

function Ensure-FfmpegVendor {
    if ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe)) {
        Write-Host "FFmpeg em vendor\ffmpeg\bin OK"
        return
    }

    Write-Host "Baixando FFmpeg (essentials) para vendor\..."
    $zip = Join-Path $env:TEMP "ffmpeg-essentials-build.zip"
    $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing

    $extractRoot = Join-Path $env:TEMP "ffmpeg-extract-$(Get-Random)"
    Expand-Archive -Path $zip -DestinationPath $extractRoot -Force

    $binDir = Get-ChildItem -Path $extractRoot -Recurse -Directory -Filter "bin" |
        Where-Object { Test-Path (Join-Path $_.FullName "ffmpeg.exe") } |
        Select-Object -First 1

    if (-not $binDir) {
        throw "ffmpeg.exe nao encontrado no zip baixado"
    }

    New-Item -ItemType Directory -Path $vendorBin -Force | Out-Null
    Copy-Item (Join-Path $binDir.FullName "ffmpeg.exe") $ffmpegExe -Force
    Copy-Item (Join-Path $binDir.FullName "ffprobe.exe") $ffprobeExe -Force

    $licenseSrc = Get-ChildItem -Path $extractRoot -Recurse -Filter "LICENSE" |
        Select-Object -First 1
    if ($licenseSrc) {
        $licenseDest = Join-Path $root "vendor\ffmpeg\LICENSE.txt"
        Copy-Item $licenseSrc.FullName $licenseDest -Force
    }

    Remove-Item $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $zip -Force -ErrorAction SilentlyContinue

    if (-not ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe))) {
        throw "Falha ao preparar vendor\ffmpeg\bin"
    }
    Write-Host "FFmpeg copiado para vendor\ffmpeg\bin"
}

Ensure-FfmpegVendor

Write-Host "Gerando executavel (pode levar alguns minutos)..."
Set-Location $root
& $venvPython -m PyInstaller --noconfirm --clean YouTubeDownloader.spec

$distDir = Join-Path $root "dist\YouTubeDownloader"
$distFfmpeg = Join-Path $distDir "ffmpeg"
New-Item -ItemType Directory -Path $distFfmpeg -Force | Out-Null
Copy-Item (Join-Path $vendorBin "ffmpeg.exe") (Join-Path $distFfmpeg "ffmpeg.exe") -Force
Copy-Item (Join-Path $vendorBin "ffprobe.exe") (Join-Path $distFfmpeg "ffprobe.exe") -Force
$licenseSrc = Join-Path $root "vendor\ffmpeg\LICENSE.txt"
if (Test-Path $licenseSrc) {
    Copy-Item $licenseSrc (Join-Path $distFfmpeg "LICENSE.txt") -Force
}

$exe = Join-Path $distDir "YouTubeDownloader.exe"
$bundledFfmpeg = Join-Path $distFfmpeg "ffmpeg.exe"

if ((Test-Path $exe) -and (Test-Path $bundledFfmpeg)) {
    Write-Host ""
    Write-Host "Pronto: $exe" -ForegroundColor Green
    Write-Host "FFmpeg embutido: $bundledFfmpeg" -ForegroundColor Green
    Write-Host "Distribua a pasta inteira: dist\YouTubeDownloader\ (zip ~150-200 MB)" -ForegroundColor Green
    Write-Host "Quem receber o zip nao precisa instalar Python nem FFmpeg."
} elseif (Test-Path $exe) {
    Write-Error "Executavel gerado, mas ffmpeg\ffmpeg.exe nao esta em dist\YouTubeDownloader\"
} else {
    Write-Error "Falha: executavel nao encontrado em dist\YouTubeDownloader\"
}
