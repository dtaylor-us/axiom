"""Tests for sourcing conflict governance scoring."""

from __future__ import annotations

import logging

from app.review.nodes import calculate_consistency_bonus


def test_consistency_bonus_negative_for_internal_bought_capability() -> None:
    """consistency_bonus is negative when internal component implements bought capability."""
    bonus = calculate_consistency_bonus(
        [{
            "component_name": "Authentication",
            "recommendation": "buy",
            "recommended_solution": "Okta",
        }],
        {
            "components": [{
                "name": "Authentication Service",
                "type": "service",
                "responsibility": "Implements custom authentication logic.",
            }]
        },
    )

    assert bonus == -3


def test_consistency_bonus_positive_when_buy_decisions_are_external() -> None:
    """consistency_bonus is positive when all buy decisions are external."""
    bonus = calculate_consistency_bonus(
        [
            {
                "component_name": "Authentication",
                "recommendation": "buy",
                "recommended_solution": "Okta",
            },
            {
                "component_name": "MFA",
                "recommendation": "buy",
                "recommended_solution": "Duo",
            },
        ],
        {
            "components": [
                {"name": "Okta Integration", "type": "external"},
                {"name": "Duo Integration", "type": "external"},
            ]
        },
    )

    assert bonus == 4


def test_conflict_detection_logs_each_conflict_found(caplog) -> None:
    """conflict detection logs each conflict found."""
    with caplog.at_level(logging.WARNING):
        calculate_consistency_bonus(
            [{
                "component_name": "SSO",
                "recommendation": "buy",
                "recommended_solution": "Ping Identity",
            }],
            {
                "components": [{
                    "name": "SSO Service",
                    "type": "service",
                    "responsibility": "Implements enterprise SSO.",
                }]
            },
        )

    assert "GOVERNANCE_SOURCING_CONFLICT" in caplog.text
    assert "component=SSO Service" in caplog.text
