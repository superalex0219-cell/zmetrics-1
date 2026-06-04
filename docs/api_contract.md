# ZMetrics — API Contract

## Base URL
```
http://localhost:8000
```

Full interactive docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication
All `/api/v1/` endpoints require:
```
Authorization: Bearer <JWT>
```
JWT is obtained from Keycloak. For development:
```powershell
# Get token via direct grant (dev only)
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8080/realms/zmetrics/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "grant_type=password&client_id=zmetrics-backend&client_secret=changeme&username=admin-user&password=changeme"
).access_token
```

## Pagination
List endpoints support:
```
GET /api/v1/quarries?page=1&page_size=20
```
Response:
```json
{"items": [...], "total": 42, "page": 1, "page_size": 20}
```

## Error Response Format
```json
{"detail": "Human-readable message", "error_code": "OPTIONAL_CODE"}
```

## Role Requirements per Endpoint

| Method | Endpoint | Min Role |
|--------|----------|----------|
| GET | `/api/v1/quarries` | user |
| POST | `/api/v1/quarries` | (any authenticated) |
| PUT | `/api/v1/quarries/{id}` | admin |
| GET | `/api/v1/quarries/{id}/sections` | user |
| POST | `/api/v1/quarries/{id}/sections` | blaster |
| GET | `/api/v1/quarries/{id}/passports` | user |
| POST | `/api/v1/quarries/{id}/passports` | blaster |
| POST | `/api/v1/quarries/{id}/passports/{id}/submit` | blaster |
| POST | `/api/v1/quarries/{id}/passports/{id}/approve` | admin |
| POST | `/api/v1/quarries/{id}/passports/{id}/revise` | blaster |
| POST | `/api/v1/captures/{id}/jobs` | surveyor+ |
| GET | `/api/v1/captures/{id}/jobs/{id}` | user |
| GET | `/api/v1/reports/{id}` | user |
| POST | `/api/v1/reports/{id}/recommendations/{id}/review` | blaster |
| GET | `/api/v1/admin/*` | admin |

## Key Endpoints

### Health
```
GET /health
→ {"status": "ok", "db": "ok", "cache": "ok"}

GET /health/ready
→ {"status": "ready"}
```

### Quarries
```
GET    /api/v1/quarries
POST   /api/v1/quarries
GET    /api/v1/quarries/{quarry_id}
PUT    /api/v1/quarries/{quarry_id}
GET    /api/v1/quarries/{quarry_id}/sections
POST   /api/v1/quarries/{quarry_id}/sections
```

### Passports
```
GET    /api/v1/quarries/{quarry_id}/passports
POST   /api/v1/quarries/{quarry_id}/passports
GET    /api/v1/quarries/{quarry_id}/passports/{passport_id}
PUT    /api/v1/quarries/{quarry_id}/passports/{passport_id}
POST   /api/v1/quarries/{quarry_id}/passports/{passport_id}/submit
POST   /api/v1/quarries/{quarry_id}/passports/{passport_id}/approve
POST   /api/v1/quarries/{quarry_id}/passports/{passport_id}/revise
```

### Analysis
```
POST   /api/v1/captures/{capture_session_id}/jobs
GET    /api/v1/captures/{capture_session_id}/jobs
GET    /api/v1/captures/{capture_session_id}/jobs/{job_id}
GET    /api/v1/captures/{capture_session_id}/jobs/{job_id}/result
```

### Reports
```
GET    /api/v1/reports/{report_id}
GET    /api/v1/reports/{report_id}/recommendations
POST   /api/v1/reports/{report_id}/recommendations/{rec_id}/review
POST   /api/v1/reports/{report_id}/recommendations/{rec_id}/comments
```

### Admin
```
GET    /api/v1/admin/users
POST   /api/v1/admin/quarries/{quarry_id}/access
DELETE /api/v1/admin/quarries/{quarry_id}/access/{access_id}
GET    /api/v1/admin/audit-logs
```
