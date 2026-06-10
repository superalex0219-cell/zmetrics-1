"""
Optional LLM explanation layer for fragmentation recommendations (M5-b).

Takes the deterministic ``RuleResult`` from the M5-a rule engine and asks
Claude to turn the structured facts into a short, advisory Russian explanation.

SAFETY (non-negotiable):
- This module is *advisory only*. It never applies, approves, or fabricates
  blast-design parameters. ``parameter_suggestions`` is produced solely by the
  rule engine and is never written here.
- The system prompt forbids the model from emitting numeric BVR parameters
  (сетка / ЛНС / удельный расход ВВ); only qualitative directions are allowed.
- The returned text is *always* wrapped so it begins with ``MOCK_BADGE`` and
  ends with ``REVIEW_FOOTER`` — enforced in code, never trusted to the model.
- ``enhance_recommendation_text`` never raises: on any failure (flag off, no
  key, missing SDK, API error, empty response) it returns the deterministic
  ``rule_result.recommendation_text`` from M5-a unchanged.
- The API key is read from settings only; it is never logged and never appears
  in the returned text.

The Anthropic SDK is imported lazily *inside* the call so importing this module
never fails when the package is absent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:  # avoid importing pydantic / rule types at module load time
    from app.config import WorkerSettings
    from app.rules import RuleResult

logger = structlog.get_logger()

# System prompt: advisory framing + hard constraints. Kept in Russian because
# the recommendation text is shown to Russian-speaking blasters/engineers.
_SYSTEM_PROMPT = (
    "Ты — ассистент-аналитик. Поясняешь горному инженеру результаты анализа "
    "гранулометрии развала (грансостав после взрыва) понятным языком.\n\n"
    "ЖЁСТКИЕ ОГРАНИЧЕНИЯ:\n"
    "- Это рекомендация ТОЛЬКО для ознакомления; окончательное решение "
    "принимает специалист. Ничего не применяется автоматически.\n"
    "- ЗАПРЕЩЕНО называть конкретные числовые параметры БВР (бурение: сетка "
    "скважин, ЛНС, удельный расход ВВ, диаметр, заряд). Допустимы только "
    "качественные направления («рассмотреть корректировку сетки скважин», "
    "«проверить распределение ВВ»).\n"
    "- Опирайся ТОЛЬКО на переданные данные; ничего не выдумывай.\n"
    "- Ответ на русском языке, 2–4 предложения, по делу, без воды.\n"
    "- Не повторяй дисклеймер про синтетические данные и про проверку "
    "специалистом — они добавляются системой автоматически."
)


def enhance_recommendation_text(
    *,
    rule_result: RuleResult,
    p10_mm: float | None,
    p50_mm: float | None,
    p80_mm: float,
    confidence_score: float,
    target_p80_mm: float | None,
    settings: WorkerSettings,
    analysis_method: str = "mock",
) -> str:
    """
    Return an LLM-enhanced recommendation string, or the deterministic
    ``rule_result.recommendation_text`` on any failure / when disabled.

    Guarantees: the returned string always starts with the method badge
    (``badge_for(analysis_method)``) and ends with ``REVIEW_FOOTER`` —
    enforced in code, not trusted to the model.
    """
    # 1. Disabled / no key → silent fallback to the deterministic rule text.
    if not settings.enable_llm_recommendations or not settings.anthropic_api_key:
        return rule_result.recommendation_text

    # 2. Lazy import: a missing SDK must fall back, never crash module import.
    try:
        from anthropic import Anthropic
    except ImportError:
        logger.warning("llm_sdk_missing")
        return rule_result.recommendation_text

    # 3. Build the prompt from structured facts only.
    user_message = _build_user_message(
        rule_result=rule_result,
        p10_mm=p10_mm,
        p50_mm=p50_mm,
        p80_mm=p80_mm,
        confidence_score=confidence_score,
        target_p80_mm=target_p80_mm,
    )

    # 4. Single attempt. Any failure (construction, network, API, malformed
    #    response) → fall back. No retry, no backoff (out of scope).
    try:
        client = Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_timeout_s,
            max_retries=0,  # single attempt → fallback (no retry/backoff, per spec)
        )
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            temperature=0.2,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        body = _extract_text(response)
    except Exception as exc:  # never let an exception escape this function
        logger.warning("llm_call_failed", error=str(exc))
        return rule_result.recommendation_text

    # 5. Empty / whitespace-only response → fall back.
    if not body or not body.strip():
        logger.info("llm_empty_response")
        return rule_result.recommendation_text

    # 6. Enforce the safety wrapper regardless of what the model returned.
    wrapped = _wrap_with_safety(body, analysis_method=analysis_method)
    logger.info("llm_enhanced", model=settings.llm_model)
    return wrapped


def _build_user_message(
    *,
    rule_result: RuleResult,
    p10_mm: float | None,
    p50_mm: float | None,
    p80_mm: float,
    confidence_score: float,
    target_p80_mm: float | None,
) -> str:
    """Compact block of the only facts the model may use. No free-text input."""
    p10_str = f"{p10_mm:.0f}мм" if p10_mm is not None else "—"
    p50_str = f"{p50_mm:.0f}мм" if p50_mm is not None else "—"
    p80_str = f"{p80_mm:.0f}мм"

    if target_p80_mm is not None:
        target_str = f"{target_p80_mm:.0f}мм"
        deviation_str = (
            f"{round((p80_mm / target_p80_mm - 1) * 100, 1)}%"
            if target_p80_mm
            else "—"
        )
    else:
        target_str = "не задан"
        deviation_str = "—"

    fines_flag = "excessive_fines" in rule_result.flags

    return (
        f"flags: {rule_result.flags}\n"
        f"P10: {p10_str}  P50: {p50_str}  P80: {p80_str}\n"
        f"target_P80: {target_str}\n"
        f"deviation_pct: {deviation_str}\n"
        f"fines_flag: {fines_flag}\n"
        f"confidence: {confidence_score:.2f}"
    )


def _extract_text(response) -> str:
    """Concatenate text from text blocks in ``response.content``.

    Robust to non-text blocks (e.g. tool-use) and to mock responses: only
    blocks whose ``.text`` is a real string contribute.
    """
    parts: list[str] = []
    for block in getattr(response, "content", None) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


def _wrap_with_safety(body: str, analysis_method: str = "mock") -> str:
    """Guarantee the badge prefix and review footer around the model's prose.

    ``badge_for`` / ``REVIEW_FOOTER`` come from ``app.rules`` — single source
    of truth shared with the M5-a deterministic text.
    """
    from app.rules import REVIEW_FOOTER, badge_for

    badge = badge_for(analysis_method)
    body = body.strip()
    if not body.startswith(badge):
        body = badge + "\n" + body
    if not body.endswith(REVIEW_FOOTER):
        body = body + "\n" + REVIEW_FOOTER
    return body
