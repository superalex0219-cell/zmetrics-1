# Запуск десктоп-приложения ZMetrics.
#
#   .\scripts\run_desktop.ps1               — просто запустить приложение
#   .\scripts\run_desktop.ps1 -WithStack    — сначала поднять Docker-стек (backend,
#                                             Keycloak, MinIO, worker с GPU и реальным
#                                             CV-контуром), затем запустить приложение
#
# Требуется venv десктопа: desktop\.venv (см. подсказку ниже, если его нет).
# Приложение работает и без backend (оффлайн-очередь), поэтому недоступный
# backend — предупреждение, а не ошибка.

param(
    [switch]$WithStack
)

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$python = Join-Path $repo "desktop\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Не найден venv десктопа: $python" -ForegroundColor Red
    Write-Host "Создать его:" -ForegroundColor Yellow
    Write-Host "  cd $repo\desktop"
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\python.exe -m pip install -e .[dev]"
    exit 1
}

if ($WithStack) {
    # Флаги реального CV-контура передаются через process env — infra\.env их не содержит
    $env:ENABLE_REAL_STEREO = "true"
    $env:ENABLE_SAM3 = "true"
    $env:DEPTH_BACKEND = "igev"
    Write-Host "Поднимаю Docker-стек (GPU-оверлей, реальный CV-контур)..." -ForegroundColor Cyan
    docker compose -f "$repo\infra\docker-compose.yml" -f "$repo\infra\docker-compose.gpu.yml" `
        up -d --remove-orphans
    if (-not $?) {
        Write-Host "Docker-стек не поднялся — приложение запустится, но в оффлайн-режиме" -ForegroundColor Yellow
    }
}

# Не блокирующая проверка backend (приложение умеет работать оффлайн)
$health = "http://localhost:8000/health"
$code = & curl.exe -s -o NUL -w "%{http_code}" --noproxy "*" --max-time 3 $health 2>$null
if ($code -ne "200") {
    Write-Host "⚠ Backend не отвечает ($health) — вход будет недоступен, съёмка уйдёт в оффлайн-очередь." -ForegroundColor Yellow
    Write-Host "  Поднять стек: .\scripts\run_desktop.ps1 -WithStack" -ForegroundColor Yellow
} else {
    Write-Host "Backend онлайн." -ForegroundColor Green
}

Write-Host "Запускаю ZMetrics..." -ForegroundColor Cyan
Set-Location (Join-Path $repo "desktop")
& $python -m zmetrics_desktop
exit $LASTEXITCODE
