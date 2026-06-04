#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Bootstrap ZMetrics for the first time. Copies .env, starts services, runs migrations.
.PARAMETER SkipConfirmation
  Skip pause prompts (for CI/unattended use).
#>
param(
    [switch]$SkipConfirmation
)

$ErrorActionPreference = "Stop"

Write-Host "=== ZMetrics Bootstrap ===" -ForegroundColor Cyan

# Check prerequisites
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH. Install Docker Desktop first."
    exit 1
}

$dockerRunning = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon is not running. Start Docker Desktop first."
    exit 1
}

# Setup infra .env
if (-not (Test-Path "infra\.env")) {
    Copy-Item "infra\.env.example" "infra\.env"
    Write-Host ""
    Write-Host "Created infra\.env from example." -ForegroundColor Yellow
    Write-Host "IMPORTANT: Edit infra\.env and replace all 'changeme' values with real passwords." -ForegroundColor Yellow
    Write-Host ""
    if (-not $SkipConfirmation) {
        Read-Host "Press Enter after editing infra\.env to continue"
    }
} else {
    Write-Host "infra\.env already exists, skipping copy." -ForegroundColor Green
}

# Start infrastructure services (without backend/worker — need migrations first)
Write-Host ""
Write-Host "Starting infrastructure services (postgres, redis, minio, keycloak)..." -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml up -d postgres redis minio keycloak

# Wait for postgres to be healthy
Write-Host "Waiting for PostgreSQL to be healthy..."
$retries = 30
$attempt = 0
do {
    Start-Sleep -Seconds 2
    $healthy = docker compose -f infra\docker-compose.yml ps postgres --format json 2>$null | ConvertFrom-Json
    $attempt++
    if ($attempt -ge $retries) {
        Write-Error "PostgreSQL did not become healthy within timeout."
        exit 1
    }
} while ($healthy.Health -ne "healthy" -and $healthy.Status -notlike "*healthy*")

Write-Host "PostgreSQL is ready." -ForegroundColor Green

# Run migrations
Write-Host ""
Write-Host "Running database migrations..." -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml run --rm `
    -e DATABASE_URL="postgresql+asyncpg://$(Get-Content infra\.env | Select-String 'POSTGRES_USER=' | ForEach-Object {$_ -replace 'POSTGRES_USER=',''}):$(Get-Content infra\.env | Select-String 'POSTGRES_PASSWORD=' | ForEach-Object {$_ -replace 'POSTGRES_PASSWORD=',''})@postgres:5432/$(Get-Content infra\.env | Select-String 'POSTGRES_DB=' | ForEach-Object {$_ -replace 'POSTGRES_DB=',''})" `
    backend alembic upgrade head

Write-Host "Migrations complete." -ForegroundColor Green

# Initialize MinIO buckets
Write-Host ""
Write-Host "Initializing MinIO buckets..." -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml run --rm minio-init

# Start all services
Write-Host ""
Write-Host "Starting all services..." -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml up -d

Write-Host ""
Write-Host "=== Bootstrap complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Services available at:" -ForegroundColor Cyan
Write-Host "  API:       http://localhost:8000"
Write-Host "  API Docs:  http://localhost:8000/docs"
Write-Host "  Keycloak:  http://localhost:8080"
Write-Host "  MinIO:     http://localhost:9001"
Write-Host ""
Write-Host "Run tests: docker compose -f infra\docker-compose.yml exec backend pytest -v"
