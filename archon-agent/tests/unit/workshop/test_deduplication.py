"""Tests for scenario deduplication and coverage recovery."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.workshop.context import WorkshopContext, WorkshopScenario
from app.workshop.nodes import infer_attributes_from_scenarios_node


def _scenario(
    scenario_id: str,
    response_measure: str = "under 300ms",
    attributes: list[str] | None = None,
    evidence_quote: str = "quoted evidence",
) -> WorkshopScenario:
    return WorkshopScenario(
        scenario_id=scenario_id,
        title=f"Scenario {scenario_id}",
        stimulus="checkout latency spikes during lunch rush",
        environment="production peak traffic window",
        artifact="checkout service",
        response="payment confirmation remains usable for customers",
        response_measure=response_measure,
        exercises_attributes=attributes or ["Performance"],
        evidence_quote=evidence_quote,
    )


def test_deduplicated_scenarios_returns_same_list_without_duplicates() -> None:
    scenarios = [
        _scenario("SC-1"),
        _scenario("SC-2", attributes=["Availability"]).model_copy(update={
            "stimulus": "warehouse link fails during inventory sync",
            "response": "inventory state remains visible to dispatchers",
        }),
    ]
    context = WorkshopContext(session_id="s", user_id="u", scenarios=scenarios)

    assert context.deduplicated_scenarios == scenarios


def test_deduplicated_scenarios_removes_duplicates() -> None:
    context = WorkshopContext(
        session_id="s",
        user_id="u",
        scenarios=[_scenario("SC-1"), _scenario("SC-2")],
    )

    assert len(context.deduplicated_scenarios) == 1


def test_deduplicated_scenarios_keeps_more_complete_duplicate() -> None:
    weak = _scenario("SC-1", response_measure="")
    complete = _scenario("SC-2", response_measure="under 300ms")
    context = WorkshopContext(session_id="s", user_id="u", scenarios=[weak, complete])

    assert context.deduplicated_scenarios[0].scenario_id == "SC-2"


def test_deduplicated_scenarios_merges_exercised_attributes() -> None:
    context = WorkshopContext(
        session_id="s",
        user_id="u",
        scenarios=[
            _scenario("SC-1", attributes=["Performance"]),
            _scenario("SC-2", attributes=["Availability"]),
        ],
    )

    assert set(context.deduplicated_scenarios[0].exercises_attributes) == {
        "Performance",
        "Availability",
    }


def test_deduplicated_scenarios_logs_when_deduplication_occurs(caplog) -> None:
    context = WorkshopContext(
        session_id="s",
        user_id="u",
        scenarios=[_scenario("SC-1"), _scenario("SC-2")],
    )

    with caplog.at_level("INFO"):
        result = context.deduplicated_scenarios

    assert len(result) == 1
    assert "Scenario deduplication: 2 -> 1. session=s" in caplog.text


@pytest.mark.asyncio
async def test_infer_attributes_node_adds_tentative_scenario_implied_attribute() -> None:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=json.dumps({
        "new_attributes": [],
        "confidence_upgrades": [],
    }))
    context = WorkshopContext(
        session_id="s",
        user_id="u",
        workshop_phase="scenario_refinement",
        scenarios=[_scenario("SC-1", attributes=["Observability"])],
    )

    result = await infer_attributes_from_scenarios_node(
        context,
        {"configurable": {"llm_client": llm}},
    )

    assert result.attributes[0].name == "Observability"
    assert result.attributes[0].confidence == "tentative"


@pytest.mark.asyncio
async def test_infer_attributes_node_logs_coverage_gap_warning(caplog) -> None:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=json.dumps({
        "new_attributes": [],
        "confidence_upgrades": [],
    }))
    context = WorkshopContext(
        session_id="s",
        user_id="u",
        workshop_phase="scenario_refinement",
        scenarios=[_scenario("SC-1", attributes=["Recoverability"])],
    )

    with caplog.at_level("WARNING"):
        await infer_attributes_from_scenarios_node(
            context,
            {"configurable": {"llm_client": llm}},
        )

    assert "COVERAGE GAP" in caplog.text
