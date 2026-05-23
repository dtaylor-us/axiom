"""Unit tests for check_phase_transition_node (app.workshop.nodes)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.workshop.context import (
    ElicitedAttribute,
    InformationGap,
    WorkshopContext,
    WorkshopScenario,
)
from app.workshop.nodes import check_phase_transition_node


def _gap(category: str, filled: bool = False, priority: str = "medium") -> InformationGap:
    base = dict(
        gap_id=str(uuid.uuid4()),
        category=category,
        description=f"{category} gap",
        priority=priority,
    )
    if filled:
        return InformationGap(**base, resolution_confidence=1.0)
    return InformationGap(**base)


def _attr(confidence: str = "inferred") -> ElicitedAttribute:
    return ElicitedAttribute(
        attribute_id=str(uuid.uuid4()),
        name="performance",
        category="other",
        importance="high",
        confidence=confidence,
        description="test attr",
        evidence_quotes=["user said so"],
        scenarios=[],
    )


def _grounded_scenario(
    *,
    with_measure: bool = True,
    suffix: str = "",
) -> WorkshopScenario:
    """Scenario that is not aspirational (operational substance present)."""
    return WorkshopScenario(
        scenario_id=str(uuid.uuid4()),
        title="Seasonal processing stress",
        stimulus=f"failure {suffix} during seasonal processing window",
        environment="peak accreditation processing window",
        response=f"isolate workload partition {suffix} and resume calculations",
        response_measure=(
            "recovery completes within four hours operational"
            if with_measure
            else ""
        ),
        derived_in_turn=1,
    )


def _ctx(**kwargs) -> WorkshopContext:
    defaults = dict(
        session_id=str(uuid.uuid4()),
        user_id="user-1",
        system_name="TestSystem",
        current_turn=2,
        workshop_phase="input_analysis",
    )
    defaults.update(kwargs)
    return WorkshopContext(**defaults)


_MOCK_CONFIG = MagicMock()


@pytest.mark.asyncio
async def test_input_analysis_always_advances():
    ctx = _ctx(workshop_phase="input_analysis")
    result = await check_phase_transition_node(ctx, _MOCK_CONFIG)
    assert result.workshop_phase == "business_context"


@pytest.mark.asyncio
async def test_business_context_stays_when_gaps_open():
    gaps = [_gap("business_context", filled=False)]
    ctx = _ctx(workshop_phase="business_context", gaps=gaps)
    result = await check_phase_transition_node(ctx, _MOCK_CONFIG)
    assert result.workshop_phase == "business_context"


@pytest.mark.asyncio
async def test_business_context_advances_when_gaps_clear():
    gaps = [_gap("business_context", filled=True)]
    ctx = _ctx(workshop_phase="business_context", gaps=gaps)
    result = await check_phase_transition_node(ctx, _MOCK_CONFIG)
    assert result.workshop_phase == "usage_context"


@pytest.mark.asyncio
async def test_risk_priority_advances_when_no_critical_open():
    gaps = [_gap("risk_priority", filled=True, priority="critical")]
    attrs = [_attr("confirmed")] * 2
    ctx = _ctx(workshop_phase="risk_priority", gaps=gaps, attributes=attrs)
    result = await check_phase_transition_node(ctx, _MOCK_CONFIG)
    assert result.workshop_phase == "scenario_brainstorm"


@pytest.mark.asyncio
async def test_risk_priority_advances_with_sufficient_attrs_and_few_critical():
    """3+ strong attrs, ≤2 critical open, turn ≥ 4 → advance."""
    gaps = [
        _gap("risk_priority", filled=False, priority="critical"),
        _gap("risk_priority", filled=False, priority="critical"),
    ]
    attrs = [_attr("confirmed")] * 3
    ctx = _ctx(workshop_phase="risk_priority", gaps=gaps, attributes=attrs, current_turn=4)
    result = await check_phase_transition_node(ctx, _MOCK_CONFIG)
    assert result.workshop_phase == "scenario_brainstorm"


@pytest.mark.asyncio
async def test_scenario_brainstorm_needs_three_partial_scenarios():
    """Needs ≥3 grounded workshop scenarios to advance."""
    scenarios = [
        _grounded_scenario(suffix="one"),
        _grounded_scenario(suffix="two"),
    ]
    ctx = _ctx(workshop_phase="scenario_brainstorm", scenarios=scenarios)
    result = await check_phase_transition_node(ctx, _MOCK_CONFIG)
    assert result.workshop_phase == "scenario_brainstorm"


@pytest.mark.asyncio
async def test_scenario_brainstorm_advances_at_three_partial_scenarios():
    scenarios = [
        _grounded_scenario(suffix="one"),
        _grounded_scenario(suffix="two"),
        _grounded_scenario(suffix="three"),
    ]
    ctx = _ctx(workshop_phase="scenario_brainstorm", scenarios=scenarios)
    result = await check_phase_transition_node(ctx, _MOCK_CONFIG)
    assert result.workshop_phase == "scenario_refinement"
