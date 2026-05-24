"""Tests for artifact-grounded governance score mechanics."""

from __future__ import annotations

from app.review.context import GovernanceScoreBreakdown
from app.review.nodes import calculate_consistency_bonus


def test_score_breakdown_total_uses_consistency_bonus() -> None:
    """total includes the consistency_bonus field."""
    breakdown = GovernanceScoreBreakdown(
        requirement_coverage=10,
        characteristic_alignment=10,
        trade_off_quality=10,
        adl_enforceability=10,
        risk_awareness=10,
        consistency_bonus=6,
    )

    assert breakdown.total == 56


def test_score_breakdown_total_is_capped_at_100() -> None:
    """total is capped at 100."""
    breakdown = GovernanceScoreBreakdown(
        requirement_coverage=20,
        characteristic_alignment=20,
        trade_off_quality=20,
        adl_enforceability=20,
        risk_awareness=20,
        consistency_bonus=10,
    )

    assert breakdown.total == 100


def test_score_breakdown_total_minimum_is_zero() -> None:
    """total minimum is 0 when penalties exceed points."""
    breakdown = GovernanceScoreBreakdown(consistency_bonus=-10)

    assert breakdown.total == 0


def test_consistency_bonus_positive_for_external_buy_component() -> None:
    """consistency_bonus is positive when buy/adopt maps to external."""
    bonus = calculate_consistency_bonus(
        [
            {
                "component_name": "Payment Processing",
                "recommendation": "buy",
                "recommended_solution": "Stripe",
            }
        ],
        {"components": [{"name": "Stripe", "type": "external"}]},
    )

    assert bonus == 2


def test_consistency_bonus_negative_for_internal_buy_component() -> None:
    """consistency_bonus is negative when buy/adopt maps to internal service."""
    bonus = calculate_consistency_bonus(
        [
            {
                "component_name": "Payment Processing",
                "recommendation": "buy",
                "recommended_solution": "Stripe",
            }
        ],
        {"components": [{"name": "Stripe", "type": "service"}]},
    )

    assert bonus == -3
