# M5-b — LLM Explanation Layer (Worker)

**Layer:** `worker/` only
**Depends on:** M5-a rule engine done ✅ (stable `evaluate_fragmentation` + `RuleResult`)
**Backend changes:** none — `recommendation_text` column already exists and is displayed in web/mobile
**Frontend changes:** none — same `recommendation_text` field, just richer prose
**New migrations:** none
**Review agent:** worker safety reviewer (focus on safety invariants + fallback robustness)
**Target test count:** worker tests +~8 (LLM module, all with a mocked client — no real API calls)

---

## Goal

After M5-a, `recommendation_text` is deterministic rule prose (badge → metrics → flag sentences → footer). M5-b adds an **optional** Claude-generated explanation that turns the structured rule output into natural, advisory language for the blaster — **without ever** introducing an auto-apply path or fabricated numeric blast parameters.

The LLM layer:
1. Takes the existing `RuleResult` + metrics as **input only** (it never re-computes flags or numbers)
2. Calls the Anthropic API to produce a concise Russian explanation of *why* the fragmentation deviates and *what class of parameters* a specialist might review (qualitative, non-binding)
3. **Always** falls back to the M5-a rule text when: the feature flag is off, no API key, the SDK is missing, a network/timeout/API error occurs, or the response is empty
4. Is wrapped by code so the **mock badge and review footer are guaranteed present** regardless of what the model returns

**Safety constraints (unchanged, non-negotiable):**
- `Recommendation.status = REQUIRES_HUMAN_REVIEW` — always
- `parameter_suggestions` stays **exactly** what the rule engine produced (factual numbers). The LLM does **not** write `parameter_suggestions`.
- The LLM must **not** emit specific numeric blast-design values (burden/spacing/charge). The prompt forbids it; this is advisory text only.
- No code path reads LLM output and writes it back to a `BlastPassport`.

---

## Files to create

| File | Purpose |
|------|---------|
| `worker/app/llm.py` | LLM enhancer: build prompt, call Anthropic, enforce badge/footer, fall back on any failure |
| `worker/tests/test_llm.py` | Unit tests, **Anthropic client fully mocked** — no network, no API key needed |

## Files to modify

| File | Change |
|------|--------|
| `worker/app/config.py` | Add LLM settings (flag, key, model, timeout, max_tokens) |
| `worker/app/tasks/pipeline.py` | Call enhancer after `evaluate_fragmentation`, use result as `recommendation_text` |
| `worker/pyproject.toml` | Add `anthropic` dependency |
| `infra/docker-compose.yml` | Pass new env vars into the `worker` service |
| `infra/.env.example` | Document the new vars (key left blank) |

---

## 1. `worker/app/config.py` — additions

Add to `WorkerSettings` (keep the existing `Field(..., alias=...)` style used by `enable_real_stereo`):

```python
# --- LLM explanation layer (M5-b) ---
enable_llm_recommendations: bool = Field(default=False, alias="ENABLE_LLM_RECOMMENDATIONS")
anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
llm_model: str = Field(default="claude-sonnet-4-6", alias="LLM_MODEL")
llm_timeout_s: float = Field(default=20.0, alias="LLM_TIMEOUT_S")
llm_max_tokens: int = Field(default=512, alias="LLM_MAX_TOKENS")
```

The layer is active **only** when `enable_llm_recommendations is True AND anthropic_api_key` is set. Either condition false → silent fallback to rule text.

---

## 2. `worker/app/llm.py` (new)

Isolated module. The Anthropic SDK is imported **inside** the call function (lazy) so module import never fails when the package is absent — that also makes "SDK missing → fallback" trivially testable.

### Public function

```python
def enhance_recommendation_text(
    *,
    rule_result: RuleResult,
    p10_mm: float | None,
    p50_mm: float | None,
    p80_mm: float,
    confidence_score: float,
    target_p80_mm: float | None,
    settings: WorkerSettings,
) -> str:
    """
    Return an LLM-enhanced recommendation string, or the deterministic
    rule_result.recommendation_text on any failure / when disabled.

    Guarantees: the returned string always starts with MOCK_BADGE and ends
    with REVIEW_FOOTER (enforced in code, not trusted to the model).
    """
```

> Keep it **synchronous** — `_create_report_and_recommendation` is async but a blocking SDK call inside it is acceptable here (the worker task already runs one job at a time per process). Do **not** introduce a second event loop. Use the synchronous Anthropic client. If you prefer async, use `AsyncAnthropic` and `await` it — but sync is simpler and the reviewer will accept either as long as no nested `asyncio.run`.

### Control flow (implement exactly)

1. **Disabled / no key** → `return rule_result.recommendation_text`
   ```python
   if not settings.enable_llm_recommendations or not settings.anthropic_api_key:
       return rule_result.recommendation_text
   ```
2. **Lazy import**, fall back if missing:
   ```python
   try:
       from anthropic import Anthropic
   except ImportError:
       logger.warning("llm_sdk_missing")
       return rule_result.recommendation_text
   ```
3. **Build prompt** from structured facts (see below).
4. **Call API** inside `try/except Exception`; on **any** exception log `llm_call_failed` with `error=str(exc)` and `return rule_result.recommendation_text`. Pass the timeout (`client = Anthropic(api_key=..., timeout=settings.llm_timeout_s)`).
5. **Extract text**: concatenate `block.text` for text blocks in `response.content`. If empty/whitespace → fallback.
6. **Enforce wrapper** and return:
   ```python
   return _wrap_with_safety(body)   # ensures MOCK_BADGE prefix + REVIEW_FOOTER suffix
   ```

### `_wrap_with_safety(body: str) -> str`

- Import `MOCK_BADGE`, `REVIEW_FOOTER` from `app.rules` (single source of truth).
- Strip the body. If it does not already start with `MOCK_BADGE`, prepend `MOCK_BADGE + "\n"`.
- If it does not already end with `REVIEW_FOOTER`, append `"\n" + REVIEW_FOOTER`.
- Return the composed string.

### Prompt design

**System prompt** (Russian, advisory framing — keep these constraints verbatim in spirit):
- Роль: ассистент-аналитик, поясняющий результаты анализа гранулометрии развала горному инженеру.
- ЖЁСТКИЕ ОГРАНИЧЕНИЯ:
  - Это рекомендация **только для ознакомления**; решение принимает специалист. Ничего не применяется автоматически.
  - **Запрещено** называть конкретные числовые параметры БВР (бурение: сетка/ЛНС/удельный расход ВВ). Допустимы только качественные направления («рассмотреть корректировку сетки скважин», «проверить распределение ВВ»).
  - Опираться **только** на переданные данные; ничего не выдумывать.
  - Ответ на русском, 2–4 предложения, без воды.
- Не нужно повторять дисклеймер про синтетические данные и про проверку специалистом — они добавляются системой.

**User message**: a compact JSON-ish block of the facts the model may use:
```
flags: <rule_result.flags>
P10: <..>мм  P50: <..>мм  P80: <..>мм
target_P80: <.. | "не задан">
deviation_pct: <.. | "—">
fines_flag: <"excessive_fines" in flags>
confidence: <0..1>
```
Set `temperature` low (e.g. `0.2`) and `max_tokens = settings.llm_max_tokens`.

> The model writes only the explanatory middle. Badge + footer are guaranteed by `_wrap_with_safety`, so even a misbehaving model cannot strip the mock label or the review requirement.

### Logging
Use `structlog.get_logger()` (same as the rest of worker). Log: `llm_enhanced` (success, with `model`), `llm_call_failed` (with error), `llm_sdk_missing`, `llm_empty_response`. Never log the API key.

---

## 3. `worker/app/tasks/pipeline.py` — wire it in

In `_create_report_and_recommendation`, **after** `rule_result = evaluate_fragmentation(...)` and **after** `report` is created, compute the final text and use it for the `Recommendation`:

```python
from app.llm import enhance_recommendation_text
from app.config import get_settings  # if not already in scope

final_text = enhance_recommendation_text(
    rule_result=rule_result,
    p10_mm=p10,
    p50_mm=p50,
    p80_mm=p80,
    confidence_score=conf,
    target_p80_mm=target_p80_mm,
    settings=get_settings(),
)

recommendation = Recommendation(
    report_id=report.id,
    generated_by_id=session.captured_by_id,
    status=RecommendationStatus.REQUIRES_HUMAN_REVIEW,   # unchanged
    recommendation_text=final_text,                       # was rule_result.recommendation_text
    parameter_suggestions=rule_result.parameter_suggestions,  # UNCHANGED — never from LLM
)
```

Nothing else in the pipeline changes. `confidence_notes` stays rule-engine-driven (deterministic) — **out of scope** for the LLM (see below).

---

## 4. `worker/pyproject.toml` — dependency

Add `anthropic` to the main `dependencies` list (pure-Python, lightweight):

```toml
dependencies = [
    ...
    "anthropic>=0.40",
]
```

(Lazy import in `llm.py` keeps the worker importable even if a build omits it, but it should ship in the image.)

---

## 5. `infra/docker-compose.yml` — worker env passthrough

Add under the existing `worker.environment:` block (after `ENABLE_REAL_STEREO`):

```yaml
      ENABLE_LLM_RECOMMENDATIONS: ${ENABLE_LLM_RECOMMENDATIONS:-false}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      LLM_MODEL: ${LLM_MODEL:-claude-sonnet-4-6}
      LLM_TIMEOUT_S: ${LLM_TIMEOUT_S:-20}
      LLM_MAX_TOKENS: ${LLM_MAX_TOKENS:-512}
```

## 6. `infra/.env.example` — document

Add a commented block (key blank — never commit a real key):

```dotenv
# --- LLM explanation layer (M5-b) ---
ENABLE_LLM_RECOMMENDATIONS=false
ANTHROPIC_API_KEY=
LLM_MODEL=claude-sonnet-4-6
LLM_TIMEOUT_S=20
LLM_MAX_TOKENS=512
```

---

## 7. `worker/tests/test_llm.py` (new)

All synchronous. **No real network.** Patch the Anthropic client. Build a `WorkerSettings` per test with the needed values (e.g. `WorkerSettings(ENABLE_LLM_RECOMMENDATIONS=True, ANTHROPIC_API_KEY="test")`) or monkeypatch `get_settings`.

Helper: build a `RuleResult` via `evaluate_fragmentation(p80_mm=600, fines_percent=5, confidence_score=0.9, target_p80_mm=500, p10_mm=95, p50_mm=280)`.

| # | Test | Setup | Assert |
|---|------|-------|--------|
| 1 | `test_disabled_returns_rule_text` | flag off | output `==` `rule_result.recommendation_text` (no client constructed) |
| 2 | `test_no_api_key_returns_rule_text` | flag on, key None | output `==` rule text |
| 3 | `test_success_uses_llm_body` | mock client returns content `[TextBlock("Крупность завышена из-за …")]` | LLM prose substring present in output |
| 4 | `test_badge_and_footer_enforced` | mock returns prose **without** badge/footer | output starts with `MOCK_BADGE`, ends with `REVIEW_FOOTER` |
| 5 | `test_api_error_falls_back` | mock client raises `RuntimeError` | output `==` rule text; no exception propagates |
| 6 | `test_empty_response_falls_back` | mock returns empty/whitespace text | output `==` rule text |
| 7 | `test_sdk_missing_falls_back` | patch import to raise `ImportError` | output `==` rule text |
| 8 | `test_prompt_contains_structured_facts` | capture the `messages.create(...)` kwargs | prompt text contains the flags and `P80`/deviation values |
| 9 | `test_api_key_never_in_output` | success path | `"test"`/key value not present in returned string |

Mocking pattern (sync client):
```python
from unittest.mock import MagicMock, patch

fake_block = MagicMock(); fake_block.text = "Крупность завышена..."
fake_resp = MagicMock(); fake_resp.content = [fake_block]
fake_client = MagicMock()
fake_client.messages.create.return_value = fake_resp

with patch("anthropic.Anthropic", return_value=fake_client):
    out = enhance_recommendation_text(...)
```
For test 7 (SDK missing): `patch.dict(sys.modules, {"anthropic": None})` then expect `ImportError` inside the lazy import → fallback. (Or patch the import site.)

---

## Safety checklist for the executor

Before marking done, verify:

- [ ] `Recommendation` still created with `status=RecommendationStatus.REQUIRES_HUMAN_REVIEW` — no change
- [ ] `parameter_suggestions` is still `rule_result.parameter_suggestions` — the LLM never produces it
- [ ] Every failure mode (disabled, no key, ImportError, API exception, empty response) returns the deterministic rule text — **no exception escapes** `enhance_recommendation_text`
- [ ] Output **always** contains `MOCK_BADGE` and `REVIEW_FOOTER` (enforced by code)
- [ ] API key is read from settings/env only, never logged, never in output
- [ ] No nested `asyncio.run`; no new event loop
- [ ] System prompt forbids numeric blast-design parameters
- [ ] No write path from LLM output to `BlastPassport`

---

## Acceptance criteria

1. `pytest worker/tests/test_llm.py -v` — all new tests pass (no network)
2. `pytest worker/tests/` — full suite green (existing 23 + new ~9), `test_rules.py` unchanged
3. `python -c "import app.llm"` succeeds **even if `anthropic` is not installed** (lazy import)
4. With `ENABLE_LLM_RECOMMENDATIONS=false` (default), pipeline output is byte-identical to M5-a rule text
5. With the flag on + a valid key, a real job's `recommendation_text` is richer prose **and** still begins with `⚠ Синтетические данные …` and ends with `… проверка специалистом.`
6. Worker image builds with `anthropic` present

---

## Explicitly out of scope

- No changes to `backend/`, `frontend/`, `mobile/`
- No new Alembic migrations
- LLM does **not** touch `confidence_notes` (stays deterministic from M5-a) or `parameter_suggestions`
- No numeric burden/spacing/charge generation — qualitative direction only
- No streaming, no caching, no retry/backoff (single attempt → fallback). Retry can be a later task if cost/latency warrants.
- No prompt-injection hardening beyond the fixed system prompt (inputs are our own numeric facts, not user free-text)
