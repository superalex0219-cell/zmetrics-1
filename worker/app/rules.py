"""
Rule-based fragmentation evaluation for the worker.

Pure logic — no I/O, no async, no SQLAlchemy. Compares the actual P80 from the
mock pipeline against the BlastPassport target and produces human-readable
recommendation text plus a read-only ``parameter_suggestions`` dict.

SAFETY: This module never applies parameters. ``parameter_suggestions`` is
reference material for human review only. Recommendations created from this
output are always written with status REQUIRES_HUMAN_REVIEW by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass

MOCK_BADGE = "⚠ Синтетические данные — результаты получены mock-пайплайном."
REVIEW_FOOTER = "Перед изменением параметров взрывания требуется проверка специалистом."

OVERSIZE_FACTOR = 1.1  # P80 more than 10% over target → oversize
FINES_THRESHOLD = 15.0  # fines_percent above this → excessive_fines


@dataclass
class RuleResult:
    flags: list[str]  # "oversize", "excessive_fines", "on_target"
    parameter_suggestions: dict | None  # JSONB for Recommendation; None when target unknown
    recommendation_text: str
    confidence_notes: str | None  # set when confidence_score < 0.8


def evaluate_fragmentation(
    p80_mm: float,
    fines_percent: float,
    confidence_score: float,
    target_p80_mm: float | None,
    p10_mm: float | None = None,
    p50_mm: float | None = None,
) -> RuleResult:
    """Compare actual fragmentation metrics against the passport target."""

    flags: list[str] = []

    oversize = target_p80_mm is not None and p80_mm > target_p80_mm * OVERSIZE_FACTOR
    if oversize:
        flags.append("oversize")

    excessive_fines = fines_percent > FINES_THRESHOLD
    if excessive_fines:
        flags.append("excessive_fines")

    if not flags:
        flags.append("on_target")

    deviation_pct: float | None = None
    if target_p80_mm is not None:
        deviation_pct = round((p80_mm / target_p80_mm - 1) * 100, 1)

    # --- parameter_suggestions (reference only) ---
    parameter_suggestions: dict | None
    if target_p80_mm is None:
        parameter_suggestions = None
    else:
        parameter_suggestions = {
            "basis": (
                f"Фактический P80 {round(p80_mm, 1)}мм относительно целевого "
                f"{round(target_p80_mm, 1)}мм (отклонение {deviation_pct}%)."
            ),
            "observed_p80_mm": round(p80_mm, 1),
            "target_p80_mm": round(target_p80_mm, 1),
            "deviation_pct": deviation_pct,
        }

    # --- recommendation_text ---
    metric_parts: list[str] = []
    if p10_mm is not None:
        metric_parts.append(f"P10={p10_mm:.0f}мм")
    if p50_mm is not None:
        metric_parts.append(f"P50={p50_mm:.0f}мм")
    metric_parts.append(f"P80={p80_mm:.0f}мм")
    metrics_line = ", ".join(metric_parts) + f". Уровень достоверности: {confidence_score:.2f}."

    lines: list[str] = [MOCK_BADGE, metrics_line]

    if target_p80_mm is None:
        lines.append("Целевой P80 в паспорте БВР не задан — сравнение недоступно.")
    elif oversize:
        lines.append(
            f"⚠ КРУПНЫЙ КЛАСС: P80 ({p80_mm:.0f}мм) превышает целевой показатель "
            f"паспорта БВР ({target_p80_mm:.0f}мм) на {deviation_pct}%."
        )
    else:
        lines.append(
            f"P80 ({p80_mm:.0f}мм) в пределах целевого показателя паспорта БВР "
            f"({target_p80_mm:.0f}мм), отклонение {deviation_pct}%."
        )

    if excessive_fines:
        lines.append(
            f"⚠ ПЕРЕИЗМЕЛЬЧЕНИЕ: доля мелких фракций ({fines_percent:.1f}%) "
            f"превышает порог {FINES_THRESHOLD:.0f}%."
        )

    lines.append(REVIEW_FOOTER)
    recommendation_text = "\n".join(lines)

    # --- confidence_notes ---
    confidence_notes: str | None = None
    if confidence_score < 0.8:
        confidence_notes = (
            f"Достоверность {confidence_score:.0%} — ниже порога 80%. "
            "Рекомендуется повторная съёмка."
        )
        if confidence_score < 0.5:
            confidence_notes += " Результаты ненадёжны."

    return RuleResult(
        flags=flags,
        parameter_suggestions=parameter_suggestions,
        recommendation_text=recommendation_text,
        confidence_notes=confidence_notes,
    )
