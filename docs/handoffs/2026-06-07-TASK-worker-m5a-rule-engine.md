# M5-a — Rule-based Recommendations (Worker Rule Engine)

**Layer:** `worker/` only  
**Depends on:** M1 + BACK-SEC-2 done ✅  
**Backend changes:** none — `parameter_suggestions` (JSONB) and `confidence_notes` columns already exist  
**New migrations:** none required  
**Target test count:** worker tests 5 → ~15

---

## Goal

The worker currently writes a static placeholder recommendation:

```
"⚠ Mock pipeline — results are synthetic. P10=…mm, P50=…mm, P80=…mm. Confidence=0.72. Review fragmentation metrics…"
```

After M5-a the worker will:
1. Join up the DB chain to read `BlastPassport.target_p80_mm` for this job
2. Apply rule logic comparing actual P80 vs the passport target
3. Write a structured `parameter_suggestions` JSONB (read-only for humans — never applied automatically)
4. Write a meaningful `recommendation_text` with concrete numbers and flags
5. Auto-populate `confidence_notes` when `confidence_score < 0.8`

**Safety constraint is unchanged:** `Recommendation.status = REQUIRES_HUMAN_REVIEW` — always, no exceptions.

---

## Files to create

| File | Purpose |
|------|---------|
| `worker/app/rules.py` | Pure rule logic — no I/O, fully unit-testable |
| `worker/tests/test_rules.py` | Unit tests for all rule branches (no DB/network) |

## Files to modify

| File | Change |
|------|--------|
| `worker/app/db_models.py` | Add `BlastEvent` and `BlastPassport` stubs + `blast_event_id` to `CaptureSession` |
| `worker/app/tasks/pipeline.py` | Wire rule engine in `_create_report_and_recommendation` |

---

## 1. `worker/app/rules.py` (new)

Pure Python — no SQLAlchemy, no Celery, no async. Fully testable with plain `pytest`.

### Dataclass

```python
from dataclasses import dataclass

@dataclass
class RuleResult:
    flags: list[str]                  # "oversize", "excessive_fines", "on_target"
    parameter_suggestions: dict | None  # JSONB for Recommendation; None when target unknown
    recommendation_text: str
    confidence_notes: str | None        # set when confidence_score < 0.8
```

### Function signature

```python
def evaluate_fragmentation(
    p80_mm: float,
    fines_percent: float,
    confidence_score: float,
    target_p80_mm: float | None,
    p10_mm: float | None = None,
    p50_mm: float | None = None,
) -> RuleResult:
```

### Rule logic (implement exactly as specified)

**Flag: `"oversize"`**
- Only when `target_p80_mm is not None`
- Condition: `p80_mm > target_p80_mm * 1.1`
- That is: P80 exceeds target by more than 10%

**Flag: `"excessive_fines"`**
- Condition: `fines_percent > 15.0`
- Independent of target

**Flag: `"on_target"`**
- Emitted when neither `"oversize"` nor `"excessive_fines"` apply
- Never emitted alongside the other flags

**`parameter_suggestions`**
- `None` when `target_p80_mm is None` — we have no reference point for suggestions
- When target is known, produce:
  ```python
  {
      "basis": "<human-readable explanation with numbers>",
      "observed_p80_mm": round(p80_mm, 1),
      "target_p80_mm": round(target_p80_mm, 1),
      "deviation_pct": round((p80_mm / target_p80_mm - 1) * 100, 1),
      # Only include blast design hints if oversize; omit if on_target or fines_only:
      # "burden_m": <float>  ← omit; we have no data to compute it yet (M5-b)
  }
  ```
  Keep it factual — do not fabricate burden/spacing numbers. That is M5-b (LLM layer).

**`recommendation_text`**
Build a plain-language string. Include:
- Mock badge at start: `"⚠ Синтетические данные — результаты получены mock-пайплайном."`
- P10/P50/P80 values if provided
- For each active flag, one sentence explaining the finding
- If `target_p80_mm is not None`: include deviation percentage
- End with: `"Перед изменением параметров взрывания требуется проверка специалистом."`

Example for oversize:
```
⚠ Синтетические данные — результаты получены mock-пайплайном.
P10=95мм, P50=280мм, P80=612мм. Уровень достоверности: 0.72.
⚠ КРУПНЫЙ КЛАСС: P80 (612мм) превышает целевой показатель паспорта БВР (500мм) на 22.4%.
Перед изменением параметров взрывания требуется проверка специалистом.
```

Example for on_target, no target known:
```
⚠ Синтетические данные — результаты получены mock-пайплайном.
P10=95мм, P50=280мм, P80=412мм. Уровень достоверности: 0.82.
Целевой P80 в паспорте БВР не задан — сравнение недоступно.
Перед изменением параметров взрывания требуется проверка специалистом.
```

**`confidence_notes`**
- `None` when `confidence_score >= 0.8`
- When `confidence_score < 0.8`:
  ```
  "Достоверность {score:.0%} — ниже порога 80%. Рекомендуется повторная съёмка."
  ```
- When `confidence_score < 0.5` (in addition): append `" Результаты ненадёжны."`

---

## 2. `worker/app/db_models.py` — additions

Add three things:

### 2a. `blast_event_id` column to existing `CaptureSession`

```python
class CaptureSession(Base):
    __tablename__ = "capture_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    blast_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # ADD
    captured_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
```

### 2b. New stub: `BlastEvent`

```python
class BlastEvent(Base):
    __tablename__ = "blast_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    passport_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
```

### 2c. New stub: `BlastPassport`

```python
class BlastPassport(Base):
    __tablename__ = "blast_passport"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    target_p80_mm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
```

No ForeignKey declarations needed in worker stubs — these are read-only query helpers.

---

## 3. `worker/app/tasks/pipeline.py` — `_create_report_and_recommendation`

### 3a. Imports to add at top of function

```python
from app.db_models import (
    AnalysisResult, BlastEvent, BlastPassport,
    CaptureSession, Recommendation, RecommendationStatus, Report,
)
from app.rules import evaluate_fragmentation
```

### 3b. Fetch `target_p80_mm` via join

After fetching `ar` and `session`, add:

```python
# Resolve BlastPassport to get target_p80_mm for rule evaluation
blast_event = (await db.execute(
    select(BlastEvent).where(BlastEvent.id == session.blast_event_id)
)).scalar_one_or_none()

passport = None
if blast_event is not None:
    passport = (await db.execute(
        select(BlastPassport).where(BlastPassport.id == blast_event.passport_id)
    )).scalar_one_or_none()

target_p80_mm = float(passport.target_p80_mm) if (passport and passport.target_p80_mm is not None) else None
```

### 3c. Call rule engine and build Recommendation

Replace the current static `rec_text` block with:

```python
rule_result = evaluate_fragmentation(
    p80_mm=p80,
    fines_percent=float(ar.fines_percent) if ar.fines_percent is not None else 0.0,
    confidence_score=conf,
    target_p80_mm=target_p80_mm,
    p10_mm=p10,
    p50_mm=p50,
)

# SAFETY: always REQUIRES_HUMAN_REVIEW — never auto-accept.
recommendation = Recommendation(
    report_id=report.id,
    generated_by_id=session.captured_by_id,
    status=RecommendationStatus.REQUIRES_HUMAN_REVIEW,
    recommendation_text=rule_result.recommendation_text,
    parameter_suggestions=rule_result.parameter_suggestions,
)
```

### 3d. Append confidence_notes to AnalysisResult if rule engine set them

```python
if rule_result.confidence_notes:
    existing = ar.confidence_notes or ""
    ar.confidence_notes = (existing + " | " + rule_result.confidence_notes).lstrip(" | ")
```

### 3e. Log flags

```python
logger.info(
    "pipeline_report_created",
    job_id=str(job_id),
    report_id=str(report.id),
    p80=p80,
    target_p80_mm=target_p80_mm,
    flags=rule_result.flags,
    confidence=conf,
)
```

---

## 4. `worker/tests/test_rules.py` (new)

All tests are synchronous (no `pytest.mark.asyncio` needed). No fixtures, no DB.

Import: `from app.rules import evaluate_fragmentation, RuleResult`

| # | Test name | Input | Assert |
|---|-----------|-------|--------|
| 1 | `test_oversize_flag` | `p80=600, fines=5, conf=0.9, target=500` | `"oversize" in result.flags` |
| 2 | `test_exact_target_not_oversize` | `p80=500, target=500` | `"oversize" not in result.flags` |
| 3 | `test_8pct_over_not_oversize` | `p80=540, target=500` (8%) | `"oversize" not in result.flags` |
| 4 | `test_10pct_over_is_oversize` | `p80=551, target=500` (10.2%) | `"oversize" in result.flags` |
| 5 | `test_excessive_fines_flag` | `p80=200, fines=16, conf=0.9, target=300` | `"excessive_fines" in result.flags` |
| 6 | `test_fines_boundary_not_flagged` | `fines=15.0` | `"excessive_fines" not in result.flags` |
| 7 | `test_both_flags` | `p80=600, fines=18, target=500` | both `"oversize"` and `"excessive_fines"` in flags, `"on_target" not in flags` |
| 8 | `test_on_target_flag` | `p80=450, fines=5, target=500` | `result.flags == ["on_target"]` |
| 9 | `test_no_target_no_oversize_flag` | `target=None, p80=999, fines=5` | `"oversize" not in result.flags` |
| 10 | `test_no_target_no_suggestions` | `target=None` | `result.parameter_suggestions is None` |
| 11 | `test_suggestions_contain_basis` | `target=500, p80=600` | `"basis" in result.parameter_suggestions` |
| 12 | `test_suggestions_contain_deviation` | `target=500, p80=600` | `result.parameter_suggestions["deviation_pct"] == pytest.approx(20.0, abs=0.1)` |
| 13 | `test_confidence_notes_below_threshold` | `conf=0.75` | `result.confidence_notes is not None` and `"0.75" or "75%" in result.confidence_notes` |
| 14 | `test_confidence_notes_at_threshold` | `conf=0.80` | `result.confidence_notes is None` |
| 15 | `test_recommendation_text_has_mock_badge` | any inputs | `"⚠" in result.recommendation_text` |

---

## Safety checklist for the executor

Before marking done, verify:

- [ ] `Recommendation` is never created without `status=RecommendationStatus.REQUIRES_HUMAN_REVIEW`
- [ ] `parameter_suggestions` contains no code path that writes values back to `BlastPassport`
- [ ] `evaluate_fragmentation` is a pure function (no side effects, no DB imports)
- [ ] `confidence_notes` is appended, not replaced, so the original mock note is preserved
- [ ] All 15 unit tests pass with `pytest worker/tests/test_rules.py -v`
- [ ] Existing 5 pipeline tests still pass unchanged

---

## Acceptance criteria

1. `pytest worker/tests/test_rules.py -v` — 15 tests pass
2. `pytest worker/tests/` — all tests pass (existing 5 + new 15)
3. `evaluate_fragmentation` imports cleanly with `python -c "from worker.app.rules import evaluate_fragmentation"`
4. Full end-to-end: after running the pipeline on a job whose passport has `target_p80_mm=500` and the mock produces P80 ≈ 600mm, the `Recommendation` in the DB has:
   - `status = "requires_human_review"` ✅
   - `parameter_suggestions["deviation_pct"] ≈ 20.0`
   - `parameter_suggestions["basis"]` non-empty string
   - `"КРУПНЫЙ КЛАСС"` in `recommendation_text`
5. For a job whose passport has `target_p80_mm = NULL`, `parameter_suggestions IS NULL` in DB

---

## Explicitly out of scope

- No changes to `backend/`
- No new Alembic migrations
- No LLM calls (that is M5-b)
- No burden/spacing calculation — `parameter_suggestions` contains factual numbers only, no design advice
