# Product Safety Rules

These rules apply to ALL files. They reflect real-world safety constraints for a system
used in active quarry blast operations.

## Blast parameter recommendations — HARD LIMITS

1. **NEVER** write code that automatically applies, accepts, or activates blast design parameters
2. **NEVER** create an endpoint or function that bulk-approves passports
3. **NEVER** transition a `Recommendation` status past `requires_human_review` without explicit user action
4. **NEVER** prefill blast design fields in a new passport from AI recommendations — user must type them manually

The rationale: incorrect blast parameters can cause structural damage, flyrock, and casualties.

## Recommendation creation

Every `Recommendation` record MUST:
- Be created with `status = RecommendationStatus.REQUIRES_HUMAN_REVIEW` (enforced by DB default)
- Include `recommendation_text` explaining the basis for the suggestion in plain language
- Include `confidence_notes` if confidence < 0.8
- Set `parameter_suggestions` as JSONB — these are **suggestions only**, displayed as reference

The `parameter_suggestions` dict may contain values like `{"burden_m": 3.2}` but these are for human review only. There must be no code path that reads this dict and updates a `BlastPassport` automatically.

## Passport workflow

State transitions require explicit human HTTP actions:
- `DRAFT → SUBMITTED`: blaster presses "Submit"
- `SUBMITTED → APPROVED`: admin presses "Approve"
- `APPROVED → ACTIVE`: authorized action
- No automated state transitions based on time or AI output

## Audit trail

The following actions MUST produce an `AuditLog` entry:
- Passport status changes (`action = "status_changed"`)
- Passport revisions (`action = "revision_created"`)
- Recommendation status changes (`action = "recommendation_reviewed"`)
- Role grants and revocations (`action = "role_assigned"` / `"role_revoked"`)
- Quarry access changes (`action = "access_granted"` / `"access_revoked"`)

`AuditLog` records are append-only. There must be no `DELETE` or `UPDATE` operation on this table.

## AI/ML outputs labeling

- Analysis reports from the mock pipeline MUST include: `"⚠ Mock pipeline — results are synthetic"`
- Future real CV outputs MUST include: model version, calibration ID, confidence score
- PDF/HTML reports MUST display the analysis method (mock vs real) prominently

## Error handling

- A failed `AnalysisJob` must NOT generate a `Report` or `Recommendation`
- If pipeline fails mid-way, partial `AnalysisResult` must NOT be created
- `confidence_score < 0.5` MUST trigger `confidence_notes` warning in the report
