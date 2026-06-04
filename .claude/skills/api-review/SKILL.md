# Skill: api-review

Review the current backend API implementation against the API contract in `docs/api_contract.md`.
Checks endpoint coverage, auth correctness, response shapes, and safety constraints.

## Usage

```
/api-review
/api-review passports
/api-review analysis
```

With no argument, reviews all API layers. With a keyword, scopes the review to that area.

## What this skill does

1. Reads `docs/api_contract.md` to get the list of expected endpoints and their auth requirements
2. Reads all router files in `backend/app/routers/`
3. Reads relevant schema files in `backend/app/schemas/`
4. Compares implemented endpoints against the contract
5. Checks each endpoint for:
   - Correct HTTP method and path
   - Correct auth dependency (`get_current_user` or `require_quarry_role`)
   - Correct minimum role level (from contract table)
   - Response schema uses `model_config = ConfigDict(from_attributes=True)`
   - 404 for missing resources
   - 409 for state conflicts
   - AuditLog written for mutating operations

## Instructions

When this skill is invoked:

1. Read `docs/api_contract.md`
2. Glob `backend/app/routers/*.py` and read each file
3. Glob `backend/app/schemas/*.py` and read each file
4. For each endpoint in the contract, check if it is implemented

5. Output a table:

```
## API Coverage Report

| Endpoint | Status | Auth | Notes |
|----------|--------|------|-------|
| GET /api/v1/quarries | ✅ | get_current_user | ok |
| POST /api/v1/quarries/{id}/passports | ✅ | require_quarry_role(BLASTER) | ok |
| POST /api/v1/.../approve | ⚠ | require_quarry_role(ADMIN) | missing AuditLog |
| DELETE /api/v1/admin/.../access/{id} | ❌ | — | not implemented |
```

6. Then list:

```
## Issues Found

### Critical (auth or safety violations)
- ...

### Missing endpoints
- ...

### Minor (schema, naming, missing audit)
- ...
```

7. End with a summary count:
```
Coverage: {implemented}/{total} endpoints
Critical issues: N
Missing endpoints: N
```
