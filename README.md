# ZMetrics — Quarry Blast Fragmentation Analysis

Platform for managing blast work passports (паспорт БВР), capturing stereo images of blast muck piles (развал), running automated CV/ML granulometric analysis, and providing AI-assisted blast design recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Flutter Android App                                         │
│  (offline capture → sync to backend)                        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS / JWT
┌────────────────────────▼────────────────────────────────────┐
│  FastAPI Backend  :8000                                      │
│  Auth: Keycloak JWT  │  Storage: MinIO  │  DB: PostgreSQL    │
└────────────────────────┬────────────────────────────────────┘
                         │ Celery task
┌────────────────────────▼────────────────────────────────────┐
│  Worker (CV/ML Pipeline)                                     │
│  calibration → rectification → depth → point_cloud          │
│  → segmentation → particle_volumes → granulometry           │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows)
- Git

## Quick Start (PowerShell)

### First-time setup

```powershell
# Clone the repo
git clone <repo-url> zmetrics
cd zmetrics

# Bootstrap (creates .env, starts services, runs migrations)
.\scripts\bootstrap.ps1
```

Or step by step:

```powershell
# 1. Copy and edit environment file
Copy-Item infra\.env.example infra\.env
# Edit infra\.env — replace all "changeme" values

# 2. Start all services
docker compose -f infra\docker-compose.yml up -d

# 3. Run migrations
docker compose -f infra\docker-compose.yml exec backend alembic upgrade head
```

### Daily development

```powershell
# Start with hot-reload (override file)
docker compose -f infra\docker-compose.yml -f infra\docker-compose.override.yml up -d

# View logs
docker compose -f infra\docker-compose.yml logs -f backend worker

# Stop all
docker compose -f infra\docker-compose.yml down

# Full reset (destroys volumes — will lose DB data)
docker compose -f infra\docker-compose.yml down -v
```

## Service URLs

| Service | URL |
|---------|-----|
| **API** | http://localhost:8000 |
| **Swagger UI** | http://localhost:8000/docs |
| **Keycloak Admin** | http://localhost:8080 (admin / changeme) |
| **MinIO Console** | http://localhost:9001 (minioadmin / changeme) |

## Running Tests

```powershell
# Backend tests
docker compose -f infra\docker-compose.yml exec backend pytest -v

# Worker tests
docker compose -f infra\docker-compose.yml exec worker pytest -v
```

## Database Migrations

```powershell
# Apply pending migrations
docker compose -f infra\docker-compose.yml exec backend alembic upgrade head

# Create a new migration after model changes
.\scripts\migrate.ps1 -Message "add_blast_event_notes"

# Or directly:
docker compose -f infra\docker-compose.yml exec backend alembic revision --autogenerate -m "description"
```

## Project Structure

```
zmetrics/
├── backend/          FastAPI app, SQLAlchemy models, Alembic migrations
├── worker/           Celery tasks, CV/ML pipeline (mock → real)
├── mobile/           Flutter Android-first app
├── infra/            Docker Compose, Keycloak realm, MinIO init
├── docs/             Architecture docs, API contract, roadmap
├── scripts/          PowerShell bootstrap and migration helpers
└── .claude/          Claude Code project rules and memory
```

## Roles

| Role | Level | Permissions |
|------|-------|-------------|
| user | 1 | Read reports |
| surveyor | 2 | Upload frames, trigger analysis |
| blaster | 3 | Manage passports, review recommendations |
| admin | 4 | User management, quarry creation |

Roles are **per quarry** — a user may have different roles on different quarries.

## Safety Note

All AI-generated blast recommendations are **decision-support only**. They are created with `status = requires_human_review` and must never be auto-applied. Final blast design decisions remain with the licensed blast engineer.
