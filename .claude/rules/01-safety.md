# Safety and Compliance Rules

These rules apply to all files in the project.

## Blast Parameter Safety
- NEVER generate code that automatically accepts, approves, or applies blast design parameters (burden, spacing, explosive charge, etc.)
- All `Recommendation` records MUST be created with `status = 'requires_human_review'` — this is the database default and must never be overridden on creation
- The `BlastPassport` workflow requires explicit human action for every state transition: DRAFT → SUBMITTED → APPROVED → ACTIVE → COMPLETED
- Do not implement any "auto-approve" or "bulk-approve" endpoint for passports or recommendations

## Secrets and Credentials
- Never hardcode credentials, API keys, passwords, or tokens in source files
- All sensitive config must come from environment variables via `pydantic-settings`
- Do not log passwords, tokens, or PII

## Audit Trail
- Write `AuditLog` entries for: passport status changes, recommendation status changes, role grants/revocations, quarry access changes
- `AuditLog` records must never be deleted or updated — they are append-only

## Data Integrity
- Analysis results are scientific outputs — do not round or truncate P10/P50/P80 values in storage (use full Numeric precision)
- `confidence_score` and uncertainty fields must be included whenever they can be computed
- Never silently discard pipeline errors — always set `analysis_job.status = 'failed'` with `error_message`
