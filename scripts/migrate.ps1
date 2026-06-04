#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Generate a new Alembic migration from model changes.
.PARAMETER Message
  Migration description (e.g., "add_capture_session_notes").
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Message
)

$ErrorActionPreference = "Stop"

Write-Host "Creating migration: $Message" -ForegroundColor Cyan
docker compose -f infra\docker-compose.yml exec backend `
    alembic revision --autogenerate -m $Message

Write-Host "Migration created. Review it in backend\migrations\versions\ before applying." -ForegroundColor Yellow
Write-Host "Apply with: docker compose -f infra\docker-compose.yml exec backend alembic upgrade head"
