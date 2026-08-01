"""
Unit tests for intent-based semantic reconciliation.

Tests cover effective_resolution_threshold adjustments per gap_question_type
and that the filled property uses those thresholds correctly.
"""
from __future__ import annotations

import pytest
from app.workshop.context import InformationGap


def _gap(
    gap_question_type: str = "unknown",
    priority: str = "high",
    resolution_confidence: float = 0.0,
) -> InformationGap:
    return InformationGap(
        gap_id="g-1",
        category="technical_context",
        description="How does the system behave under load?",
        priority=priority,
        resolution_confidence=resolution_confidence,
        gap_question_type=gap_question_type,
    )


class TestEffectiveResolutionThreshold:
    def test_high_priority_unknown_uses_base_0_75(self):
        gap = _gap(gap_question_type="unknown", priority="high")
        # high priority base is 0.75 (not 0.9 which is critical)
        assert gap.effective_resolution_threshold == pytest.approx(0.75)

    def test_critical_priority_unknown_uses_base_0_90(self):
        gap = _gap(gap_question_type="unknown", priority="critical")
        assert gap.effective_resolution_threshold == pytest.approx(0.90)

    def test_low_priority_unknown_uses_base_0_60(self):
        gap = _gap(gap_question_type="unknown", priority="low")
        assert gap.effective_resolution_threshold == pytest.approx(0.60)

    def test_mechanism_gap_lowers_threshold_by_0_10(self):
        # mechanism questions are harder to resolve — accept at lower confidence
        gap = _gap(gap_question_type="mechanism", priority="critical")
        assert gap.effective_resolution_threshold == pytest.approx(0.80)

    def test_metric_gap_raises_threshold_by_0_10(self):
        # metric questions need a number — require higher confidence
        gap = _gap(gap_question_type="metric", priority="high")
        assert gap.effective_resolution_threshold == pytest.approx(0.85)

    def test_critical_mechanism_threshold_is_0_80(self):
        # 0.9 (critical base) - 0.10 (mechanism discount) = 0.80
        gap = _gap(gap_question_type="mechanism", priority="critical")
        assert gap.effective_resolution_threshold == pytest.approx(0.80)

    def test_constraint_gap_uses_base_threshold(self):
        # constraint type has no adjustment
        gap = _gap(gap_question_type="constraint", priority="high")
        assert gap.effective_resolution_threshold == pytest.approx(0.75)


class TestFilledProperty:
    def test_filled_true_when_confidence_meets_threshold(self):
        # mechanism + high priority: threshold = 0.75 - 0.10 = 0.65
        gap = _gap(gap_question_type="mechanism", priority="high", resolution_confidence=0.65)
        assert gap.filled is True

    def test_filled_false_when_confidence_below_threshold(self):
        # metric + high priority: threshold = 0.75 + 0.10 = 0.85
        gap = _gap(gap_question_type="metric", priority="high", resolution_confidence=0.70)
        assert gap.filled is False

    def test_metric_gap_not_resolved_by_vague_confidence(self):
        # metric questions require confidence >= 0.85 for high priority
        gap = _gap(gap_question_type="metric", priority="high", resolution_confidence=0.80)
        assert gap.filled is False

    def test_mechanism_gap_resolves_at_lower_confidence(self):
        # high priority mechanism: 0.75 - 0.10 = 0.65 threshold
        gap = _gap(gap_question_type="mechanism", priority="high", resolution_confidence=0.65)
        assert gap.filled is True

    def test_unknown_gap_uses_base_threshold(self):
        gap = _gap(gap_question_type="unknown", priority="high", resolution_confidence=0.74)
        assert gap.filled is False

        gap_filled = _gap(gap_question_type="unknown", priority="high", resolution_confidence=0.75)
        assert gap_filled.filled is True
