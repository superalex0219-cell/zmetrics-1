# Safety and Compliance Rules

These rules apply to ALL files. They reflect real-world safety constraints for a system
used in active quarry blast operations. Incorrect blast parameters can cause structural
damage, flyrock, and casualties.

## Blast parameter safety — HARD LIMITS

1. **NEVER** write code that automatically applies, accepts, approves, or activates blast
   design parameters (burden, spacing, explosive charge, stemming, etc.)
2. **NEVER** create an endpoint or function that bulk-approves passports or recommendations
3. **NEVER** transition a `Recommendation` past `requires_human_review` without explicit user action
4. **NEVER** prefill blast design fields in a new passport from AI recommendations — the
   user must type them manually
5. There must be **no code path** that reads `parameter_suggestions` and updates a
   `BlastPassport` automatically

## Recommendation creation

Every `Recommendation` record MUST:
- Be created with `status = RecommendationStatus.REQUIRES_HUMAN_REVIEW` — this is the DB
  default and must never be overridden on creation
- Include `recommendation_text` explaining the basis for the suggestion in plain language
- Include `confidence_notes` if confidence < 0.8
- Store `parameter_suggestions` as JSONB — these are **suggestions only**, displayed as
  reference (e.g. `{"burden_m": 3.2}`), never applied automatically

## Passport workflow

State transitions require explicit human action at every step:
`DRAFT → SUBMITTED → APPROVED → ACTIVE → COMPLETED`
- `DRAFT → SUBMITTED`: blaster presses "Submit"
- `SUBMITTED → APPROVED`: admin presses "Approve"
- `APPROVED → ACTIVE`: authorized action
- No automated state transitions based on time or AI output

When a passport is revised: create a new record with `revision_number + 1`, set the old
record `status = SUPERSEDED` and `superseded_by_id = new.id`, and write an AuditLog entry.

## Audit trail (append-only)

Write an `AuditLog` entry for:
- Passport status changes (`action = "status_changed"`)
- Passport revisions (`action = "revision_created"`)
- Recommendation status changes (`action = "recommendation_reviewed"`)
- Role grants/revocations (`action = "role_assigned"` / `"role_revoked"`)
- Quarry access changes (`action = "access_granted"` / `"access_revoked"`)

`AuditLog` records are append-only — there must be **no DELETE or UPDATE** on this table.

## Secrets and credentials

- Never hardcode credentials, API keys, passwords, or tokens in source files
- All sensitive config comes from environment variables via `pydantic-settings`
- Do not log passwords, tokens, or PII

## Data integrity

- Analysis results are scientific outputs — do not round or truncate P10/P50/P80 in
  storage or computation (full `Numeric` precision)
- `confidence_score` and uncertainty fields must be included whenever they can be computed
- Never silently discard pipeline errors — always set `analysis_job.status = 'failed'`
  with `error_message`

## AI/ML output labeling

- Mock pipeline outputs MUST include: `"⚠ Mock pipeline — results are synthetic"`
- Real CV outputs MUST include: model version, calibration ID, confidence score
- Reports MUST display the analysis method (mock vs real) prominently

## Error handling

- A failed `AnalysisJob` must NOT generate a `Report` or `Recommendation`
- If the pipeline fails mid-way, a partial `AnalysisResult` must NOT be created
- `confidence_score < 0.5` MUST trigger a `confidence_notes` warning in the report
