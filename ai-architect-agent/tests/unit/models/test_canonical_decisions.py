"""Tests for canonical sourcing decisions on ArchitectureContext."""

from __future__ import annotations

import logging

from app.models import ArchitectureContext


def _context_with(decision: dict) -> ArchitectureContext:
    """Build context with one buy-vs-build entry."""
    return ArchitectureContext(buy_vs_build_analysis=[decision])


def test_canonical_decisions_returns_empty_when_buy_vs_build_empty() -> None:
    """canonical_decisions returns empty when buy_vs_build is empty."""
    context = ArchitectureContext()

    assert context.canonical_decisions == []


def test_canonical_decisions_handles_component_name_field() -> None:
    """canonical_decisions handles the component_name field."""
    context = _context_with({
        "component_name": "Authentication",
        "recommendation": "buy",
        "recommended_solution": "Okta",
    })

    assert context.canonical_decisions[0]["component"] == "Authentication"


def test_canonical_decisions_handles_component_field() -> None:
    """canonical_decisions handles the component field."""
    context = _context_with({
        "component": "SSO",
        "recommendation": "buy",
        "recommended_solution": "Ping Identity",
    })

    assert context.canonical_decisions[0]["component"] == "SSO"


def test_canonical_decisions_handles_capability_field() -> None:
    """canonical_decisions handles the capability field."""
    context = _context_with({
        "capability": "MFA",
        "recommendation": "buy",
        "recommended_solution": "Duo",
    })

    assert context.canonical_decisions[0]["component"] == "MFA"


def test_canonical_decisions_handles_recommendation_field() -> None:
    """canonical_decisions handles the recommendation field."""
    context = _context_with({
        "name": "Authentication",
        "recommendation": "buy",
        "provider": "Okta",
    })

    assert context.canonical_decisions[0]["decision"] == "buy"


def test_canonical_decisions_handles_decision_field() -> None:
    """canonical_decisions handles the decision field."""
    context = _context_with({
        "name": "SSO",
        "decision": "buy",
        "provider": "Ping Identity",
    })

    assert context.canonical_decisions[0]["decision"] == "buy"


def test_canonical_decisions_handles_action_field() -> None:
    """canonical_decisions handles the action field."""
    context = _context_with({
        "name": "MFA",
        "action": "adopt",
        "tool": "Duo",
    })

    assert context.canonical_decisions[0]["decision"] == "adopt"


def test_canonical_decisions_only_includes_buy_and_adopt() -> None:
    """canonical_decisions only includes buy and adopt."""
    context = ArchitectureContext(buy_vs_build_analysis=[
        {"name": "Authentication", "action": "buy", "tool": "Okta"},
        {"name": "MFA", "decision": "adopt", "provider": "Duo"},
        {"name": "Audit", "recommendation": "build"},
    ])

    assert [d["decision"] for d in context.canonical_decisions] == [
        "buy",
        "adopt",
    ]


def test_canonical_decisions_excludes_build_decisions() -> None:
    """canonical_decisions excludes build decisions."""
    context = _context_with({
        "component_name": "Audit",
        "recommendation": "build",
        "recommended_solution": "Custom",
    })

    assert context.canonical_decisions == []


def test_canonical_decisions_includes_excluded_component_patterns() -> None:
    """canonical_decisions includes excluded_component_patterns."""
    context = _context_with({
        "component_name": "Authentication Service",
        "recommendation": "buy",
        "recommended_solution": "Okta",
    })

    patterns = context.canonical_decisions[0]["excluded_component_patterns"]
    assert "authentication service" in patterns
    assert "authentication" in patterns


def test_canonical_decisions_logs_warning_when_no_buy_or_adopt(
    caplog,
) -> None:
    """canonical_decisions logs WARNING when no buy/adopt entries are found."""
    context = _context_with({
        "component_name": "Audit",
        "recommendation": "build",
        "recommended_solution": "Custom",
    })

    with caplog.at_level(logging.WARNING):
        decisions = context.canonical_decisions

    assert decisions == []
    assert "but no buy/adopt entries were found" in caplog.text
