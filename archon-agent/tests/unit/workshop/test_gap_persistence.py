"""Unit tests for gap merge and persistence behaviour in identify_gaps_node."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.workshop.context import InformationGap, WorkshopContext
from app.workshop.nodes import identify_gaps_node


def _base_state(**kwargs: object) -> WorkshopContext:
    """Minimal workshop context for node tests."""
    defaults: dict = {
        "session_id": "sess-1",
        "user_id": "user-1",
        "current_turn": 2,
    }
    defaults.update(kwargs)
    return WorkshopContext(**defaults)


@pytest.mark.asyncio
async def test_identify_gaps_marks_gap_filled_when_id_in_filled_list() -> None:
    g = InformationGap(
        gap_id="GAP-A",
        category="business_context",
        description="Stakeholders?",
        priority="critical",
    )
    state = _base_state(gaps=[g])
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "new_gaps": [],
            "gaps_filled_by_latest_input": ["GAP-A"],
        })
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "answer"}}

    out = await identify_gaps_node(state, config)

    assert len(out.gaps) == 1
    assert out.gaps[0].filled is True


@pytest.mark.asyncio
async def test_identify_gaps_sets_filled_in_turn_to_current_turn() -> None:
    g = InformationGap(
        gap_id="GAP-B",
        category="usage_context",
        description="Load?",
        priority="high",
    )
    state = _base_state(current_turn=5, gaps=[g])
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "new_gaps": [],
            "gaps_filled_by_latest_input": ["GAP-B"],
        })
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "42"}}

    out = await identify_gaps_node(state, config)

    assert out.gaps[0].filled_in_turn == 5


@pytest.mark.asyncio
async def test_identify_gaps_does_not_duplicate_existing_gap_ids() -> None:
    existing = InformationGap(
        gap_id="GAP-001",
        category="business_context",
        description="Original",
        priority="critical",
    )
    state = _base_state(gaps=[existing])
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "new_gaps": [
                {
                    "gap_id": "GAP-001",
                    "category": "business_context",
                    "description": "Duplicate row",
                    "questions": ["q"],
                    "priority": "high",
                },
                {
                    "gap_id": "GAP-002",
                    "category": "technical_context",
                    "description": "Really new",
                    "questions": ["q2"],
                    "priority": "medium",
                },
            ],
            "gaps_filled_by_latest_input": [],
        })
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "x"}}

    out = await identify_gaps_node(state, config)

    ids = [x.gap_id for x in out.gaps]
    assert ids.count("GAP-001") == 1
    assert "GAP-002" in ids
    assert len(out.gaps) == 2


@pytest.mark.asyncio
async def test_identify_gaps_updates_open_gaps_to_exclude_filled() -> None:
    g1 = InformationGap(
        gap_id="g-open",
        category="risk_priority",
        description="Risks?",
        priority="critical",
    )
    g2 = InformationGap(
        gap_id="g-done",
        category="business_context",
        description="Goals?",
        priority="high",
    )
    state = _base_state(gaps=[g1, g2])
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "new_gaps": [],
            "gaps_filled_by_latest_input": ["g-done"],
        })
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "done"}}

    out = await identify_gaps_node(state, config)

    assert out.open_gaps == ["g-open"]


@pytest.mark.asyncio
async def test_identify_gaps_preserves_gaps_not_listed_as_filled() -> None:
    open_g = InformationGap(
        gap_id="stay-open",
        category="usage_context",
        description="Peak users?",
        priority="critical",
    )
    state = _base_state(gaps=[open_g])
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "new_gaps": [],
            "gaps_filled_by_latest_input": [],
        })
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "partial"}}

    out = await identify_gaps_node(state, config)

    assert len(out.gaps) == 1
    assert out.gaps[0].gap_id == "stay-open"
    assert out.gaps[0].filled is False
