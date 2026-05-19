# Atualiza dependencias Python do projeto (principalmente yt-dlp)
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Criando ambiente virtual..."
    python -m venv (Join-Path $root ".venv")
}

Write-Host "Atualizando pacotes..."
& $venvPython -m pip install -U pip
& $venvPython -m pip install -U -r (Join-Path $root "requirements.txt")

Write-Host ""
Write-Host "Versoes instaladas:"
& $venvPython -m pip show yt-dlp customtkinter Pillow | Select-String "Name:|Version:"

Write-Host ""
Write-Host "Concluido. Para distribuir, regenere o .exe com .\build.ps1"
