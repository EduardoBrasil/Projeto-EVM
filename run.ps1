$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$requirementsFile = Join-Path $projectRoot "requirements.txt"
$appFile = Join-Path $projectRoot "app.py"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtualenv nao encontrada. Criando .venv..." -ForegroundColor Yellow
    python -m venv (Join-Path $projectRoot ".venv")
}

Write-Host "Instalando dependencias..." -ForegroundColor Cyan
& $venvPython -m pip install -r $requirementsFile

Write-Host "Subindo a aplicacao..." -ForegroundColor Green
& $venvPython $appFile
