"""Unit tests for the LLM explanation layer (worker/app/llm.py).

All synchronous. The Anthropic client is fully mocked — NO network, NO real API
key. We inject a fake ``anthropic`` module into ``sys.modules`` so the lazy
``from anthropic import Anthropic`` inside ``enhance_recommendation_text`` picks
up our stub; this also means the real SDK does not need to be installed.

Every test verifies a safety invariant: any failure mode falls back to the
deterministic M5-a rule text, the badge/footer are always enforced, and the API
key never leaks into the output.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from app.config import WorkerSettings
from app.llm import enhance_recommendation_text
from app.rules import MOCK_BADGE, REVIEW_FOOTER, evaluate_fragmentation

# --- shared fixtures / helpers ------------------------------------------------

LLM_PROSE = "Крупность завышена из-за недостаточного дробления верхнего горизонта."


def _rule_result():
    """The reference RuleResult used across tests (oversize, 20% over target)."""
    return evaluate_fragmentation(
        p80_mm=600,
        fines_percent=5,
        confidence_score=0.9,
        target_p80_mm=500,
        p10_mm=95,
        p50_mm=280,
    )


def _settings(**overrides) -> WorkerSettings:
    base = {"ENABLE_LLM_RECOMMENDATIONS": True, "ANTHROPIC_API_KEY": "test"}
    base.update(overrides)
    return WorkerSettings(**base)


def _call(settings: WorkerSettings, rule_result=None) -> str:
    rr = rule_result if rule_result is not None else _rule_result()
    return enhance_recommendation_text(
        rule_result=rr,
        p10_mm=95,
        p50_mm=280,
        p80_mm=600,
        confidence_score=0.9,
        target_p80_mm=500,
        settings=settings,
    )


def _fake_block(text):
    block = MagicMock()
    block.text = text
    return block


def _fake_anthropic(*, content=None, side_effect=None):
    """Build a fake ``anthropic`` module and its client.

    Returns ``(module, client)``. ``client.messages.create`` returns a response
    whose ``.content`` is ``content`` (default: one text block of LLM_PROSE), or
    raises ``side_effect`` if given.
    """
    if content is None:
        content = [_fake_block(LLM_PROSE)]
    response = MagicMock()
    response.content = content

    client = MagicMock()
    if side_effect is not None:
        client.messages.create.side_effect = side_effect
    else:
        client.messages.create.return_value = response

    module = MagicMock()
    module.Anthropic.return_value = client
    return module, client


# --- tests --------------------------------------------------------------------


def test_disabled_returns_rule_text():
    """Flag off → deterministic rule text, client never constructed."""
    rr = _rule_result()
    module, _ = _fake_anthropic()
    with patch.dict(sys.modules, {"anthropic": module}):
        out = enhance_recommendation_text(
            rule_result=rr,
            p10_mm=95,
            p50_mm=280,
            p80_mm=600,
            confidence_score=0.9,
            target_p80_mm=500,
            settings=_settings(ENABLE_LLM_RECOMMENDATIONS=False),
        )
    assert out == rr.recommendation_text
    module.Anthropic.assert_not_called()


def test_no_api_key_returns_rule_text():
    """Flag on but no key → deterministic rule text."""
    rr = _rule_result()
    out = _call(_settings(ANTHROPIC_API_KEY=None), rule_result=rr)
    assert out == rr.recommendation_text


def test_success_uses_llm_body():
    """Happy path → the model's prose appears in the output."""
    module, _ = _fake_anthropic()
    with patch.dict(sys.modules, {"anthropic": module}):
        out = _call(_settings())
    assert LLM_PROSE in out


def test_badge_and_footer_enforced():
    """Model returns prose without badge/footer → code enforces both."""
    module, _ = _fake_anthropic(content=[_fake_block("Просто текст без рамок.")])
    with patch.dict(sys.modules, {"anthropic": module}):
        out = _call(_settings())
    assert out.startswith(MOCK_BADGE)
    assert out.endswith(REVIEW_FOOTER)


def test_api_error_falls_back():
    """Client raises → fall back to rule text, no exception propagates."""
    rr = _rule_result()
    module, _ = _fake_anthropic(side_effect=RuntimeError("boom"))
    with patch.dict(sys.modules, {"anthropic": module}):
        out = _call(_settings(), rule_result=rr)
    assert out == rr.recommendation_text


def test_empty_response_falls_back():
    """Whitespace-only model output → fall back to rule text."""
    rr = _rule_result()
    module, _ = _fake_anthropic(content=[_fake_block("   \n  ")])
    with patch.dict(sys.modules, {"anthropic": module}):
        out = _call(_settings(), rule_result=rr)
    assert out == rr.recommendation_text


def test_sdk_missing_falls_back():
    """Anthropic SDK absent (ImportError) → fall back to rule text."""
    rr = _rule_result()
    # Setting the module to None makes `from anthropic import ...` raise ImportError.
    with patch.dict(sys.modules, {"anthropic": None}):
        out = _call(_settings(), rule_result=rr)
    assert out == rr.recommendation_text


def test_prompt_contains_structured_facts():
    """The user message carries the flags, P80 and the deviation value."""
    module, client = _fake_anthropic()
    with patch.dict(sys.modules, {"anthropic": module}):
        _call(_settings())
    kwargs = client.messages.create.call_args.kwargs
    user_content = kwargs["messages"][0]["content"]
    assert "oversize" in user_content        # flag from the rule engine
    assert "P80" in user_content             # metric label
    assert "20.0" in user_content            # deviation_pct (600 vs 500)


def test_api_key_never_in_output():
    """The API key value must never appear in the returned text."""
    module, _ = _fake_anthropic()
    with patch.dict(sys.modules, {"anthropic": module}):
        out = _call(_settings(ANTHROPIC_API_KEY="super-secret-key-123"))
    assert "super-secret-key-123" not in out
