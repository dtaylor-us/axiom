"""Tests for scenario-first elicitation and completeness helpers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.workshop.context import (
    WorkshopContext,
    WorkshopScenario,
    compute_scenario_completeness,
)
from app.workshop.nodes import (
    elicit_scenarios_node,
    infer_attributes_from_scenarios_node,
)


def test_compute_completeness_all_empty() -> None:
    assert compute_scenario_completeness("", "", "", "") == "aspirational"


def test_compute_completeness_complete() -> None:
    s = "x" * 12
    m = "p99 under 300ms"
    assert compute_scenario_completeness(s, "", s, m) == "complete"


def test_compute_completeness_needs_measure() -> None:
    s = "stimulus long"
    r = "response long ok"
    assert compute_scenario_completeness(s, "", r, "") == "needs_measure"


@pytest.mark.asyncio
async def test_elicit_scenarios_merges_by_id() -> None:
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "scenarios": [{
                "scenario_id": "SC-1",
                "title": "Node failure",
                "stimulus": "AKS worker fails during seasonal run",
                "source": "kubernetes",
                "environment": "peak seasonal accreditation window",
                "artifact": "calc engine",
                "response": "isolate partition and resume",
                "response_measure": "",
                "exercises_attributes": ["Recoverability"],
                "evidence_quote": "node failed mid-calculation",
            }],
        }),
    )
    existing = WorkshopScenario(
        scenario_id="SC-0",
        title="old",
        stimulus="a" * 12,
        environment="b" * 12,
        response="c" * 12,
        response_measure="d" * 12,
        derived_in_turn=1,
    )
    ctx = WorkshopContext(
        session_id="s",
        user_id="u",
        workshop_phase="scenario_brainstorm",
        current_turn=3,
        scenarios=[existing],
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "user text"}}
    out = await elicit_scenarios_node(ctx, config)
    assert len(out.scenarios) == 2
    ids = {s.scenario_id for s in out.scenarios}
    assert "SC-1" in ids
    assert out.scenarios[-1].evidence_quote


@pytest.mark.asyncio
async def test_infer_attributes_from_scenarios_adds_attribute() -> None:
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "new_attributes": [{
                "attribute_id": "QA-1",
                "name": "Recoverability",
                "category": "recoverability",
                "description": "resume without full restart",
                "importance": "high",
                "confidence": "inferred",
                "evidence_quote": ["evidence"],
                "source_scenarios": ["SC-1"],
                "scenario": {
                    "scenario_id": "SC-1",
                    "stimulus": "stimulus text long enough here",
                    "response": "response text long enough",
                    "response_measure": "measure text long ok",
                },
                "open_questions": [],
            }],
            "confidence_upgrades": [],
        }),
    )
    ws = WorkshopScenario(
        scenario_id="SC-1",
        title="t",
        stimulus="failure during seasonal processing window",
        environment="peak seasonal accreditation window",
        response="isolate workload partition and resume calculations",
        response_measure="",
        derived_in_turn=3,
    )
    ctx = WorkshopContext(
        session_id="s",
        user_id="u",
        workshop_phase="scenario_brainstorm",
        current_turn=3,
        scenarios=[ws],
        gaps=[],
    )
    config = {"configurable": {"llm_client": llm}}
    out = await infer_attributes_from_scenarios_node(ctx, config)
    assert len(out.attributes) == 1
    assert out.attributes[0].name == "Recoverability"


@pytest.mark.asyncio
async def test_infer_skips_when_no_scenarios() -> None:
    llm = AsyncMock()
    ctx = WorkshopContext(
        session_id="s",
        user_id="u",
        workshop_phase="scenario_brainstorm",
        current_turn=1,
        scenarios=[],
    )
    out = await infer_attributes_from_scenarios_node(
        ctx, {"configurable": {"llm_client": llm}},
    )
    llm.complete.assert_not_called()
    assert out.attributes == []
