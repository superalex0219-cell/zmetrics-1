"""Unit tests for the rule engine (worker/app/rules.py).

All tests are synchronous — pure logic, no DB, no network.
"""

from __future__ import annotations

import pytest

from app.rules import RuleResult, evaluate_fragmentation


def test_oversize_flag():
    result = evaluate_fragmentation(p80_mm=600, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert "oversize" in result.flags


def test_exact_target_not_oversize():
    result = evaluate_fragmentation(p80_mm=500, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert "oversize" not in result.flags


def test_8pct_over_not_oversize():
    result = evaluate_fragmentation(p80_mm=540, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert "oversize" not in result.flags


def test_10pct_over_is_oversize():
    result = evaluate_fragmentation(p80_mm=551, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert "oversize" in result.flags


def test_excessive_fines_flag():
    result = evaluate_fragmentation(p80_mm=200, fines_percent=16, confidence_score=0.9, target_p80_mm=300)
    assert "excessive_fines" in result.flags


def test_fines_boundary_not_flagged():
    result = evaluate_fragmentation(p80_mm=200, fines_percent=15.0, confidence_score=0.9, target_p80_mm=300)
    assert "excessive_fines" not in result.flags


def test_both_flags():
    result = evaluate_fragmentation(p80_mm=600, fines_percent=18, confidence_score=0.9, target_p80_mm=500)
    assert "oversize" in result.flags
    assert "excessive_fines" in result.flags
    assert "on_target" not in result.flags


def test_on_target_flag():
    result = evaluate_fragmentation(p80_mm=450, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert result.flags == ["on_target"]


def test_no_target_no_oversize_flag():
    result = evaluate_fragmentation(p80_mm=999, fines_percent=5, confidence_score=0.9, target_p80_mm=None)
    assert "oversize" not in result.flags


def test_no_target_no_suggestions():
    result = evaluate_fragmentation(p80_mm=999, fines_percent=5, confidence_score=0.9, target_p80_mm=None)
    assert result.parameter_suggestions is None


def test_suggestions_contain_basis():
    result = evaluate_fragmentation(p80_mm=600, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert "basis" in result.parameter_suggestions


def test_suggestions_contain_deviation():
    result = evaluate_fragmentation(p80_mm=600, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert result.parameter_suggestions["deviation_pct"] == pytest.approx(20.0, abs=0.1)


def test_confidence_notes_below_threshold():
    result = evaluate_fragmentation(p80_mm=450, fines_percent=5, confidence_score=0.75, target_p80_mm=500)
    assert result.confidence_notes is not None
    assert "0.75" in result.confidence_notes or "75%" in result.confidence_notes


def test_confidence_notes_at_threshold():
    result = evaluate_fragmentation(p80_mm=450, fines_percent=5, confidence_score=0.80, target_p80_mm=500)
    assert result.confidence_notes is None


def test_recommendation_text_has_mock_badge():
    result = evaluate_fragmentation(p80_mm=450, fines_percent=5, confidence_score=0.9, target_p80_mm=500)
    assert "⚠" in result.recommendation_text
