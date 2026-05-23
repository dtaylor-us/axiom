"""Tests for question prompt wiring and redundant-question filtering."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.workshop.context import InformationGap, WorkshopContext, WorkshopTurn
from app.workshop.nodes import (
    _filter_already_answered_questions,
    _questions_overlap,
    generate_response_node,
)


def test_questions_overlap_true_for_similar() -> None:
    assert _questions_overlap(
        "what are the primary business goals",
        "describe the main business goals for this product",
    )


def test_questions_overlap_false_for_unrelated() -> None:
    assert not _questions_overlap(
        "what database does the team prefer",
        "who are the primary stakeholders for billing",
    )


def test_filter_removes_questions_about_filled_gaps() -> None:
    filled = InformationGap(
        gap_id="g1",
        category="business_context",
        description="what are the business goals for the portal",
        filled=True,
        filled_in_turn=1,
    )
    state = WorkshopContext(session_id="s", user_id="u")
    qs = [{"question": "What are the business goals for the portal?"}]
    out = _filter_already_answered_questions(qs, [filled], state)
    assert out == []


def test_filter_removes_repeat_questions_from_recent_turns() -> None:
    state = WorkshopContext(session_id="s", user_id="u")
    state.turns = [
        WorkshopTurn(
            turn_number=1,
            user_input="hi",
            agent_response="",
            questions_asked=[
                "What peak transaction volume should we plan for?",
            ],
            workshop_phase="usage_context",
        ),
    ]
    qs = [{"question": "What peak transaction volume should we plan for?"}]
    out = _filter_already_answered_questions(qs, [], state)
    assert out == []


def test_filter_preserves_genuinely_new_questions() -> None:
    state = WorkshopContext(session_id="s", user_id="u")
    filled = InformationGap(
        gap_id="x",
        category="business_context",
        description="stakeholder roster",
        filled=True,
        filled_in_turn=1,
    )
    qs = [{"question": "What recovery time objective applies after regional failover?"}]
    out = _filter_already_answered_questions(qs, [filled], state)
    assert len(out) == 1


@pytest.mark.asyncio
async def test_generate_response_passes_recent_turns_and_gap_lists_to_prompt() -> None:
    t1 = WorkshopTurn(
        turn_number=1,
        user_input="first",
        agent_response="r1",
        gaps_identified=["g1"],
        attributes_derived=[],
        questions_asked=["Q1?"],
        workshop_phase="business_context",
    )
    g_open = InformationGap(
        gap_id="go",
        category="technical_context",
        description="integrations",
        priority="high",
    )
    g_done = InformationGap(
        gap_id="gd",
        category="business_context",
        description="done topic",
        priority="low",
        filled=True,
        filled_in_turn=1,
    )
    state = WorkshopContext(session_id="sid", user_id="uid", current_turn=2)
    state.turns = [t1]
    state.gaps = [g_open, g_done]

    captured: dict = {}

    def fake_load(name: str, **kwargs: object) -> str:
        captured.update(kwargs)
        return "{}"

    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "acknowledgement": "ok",
            "progress_note": "",
            "questions": [{"question": "New?", "gap_id": "", "rationale": ""}],
        })
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "latest"}}

    with patch("app.workshop.nodes.load_prompt", side_effect=fake_load):
        await generate_response_node(state, config)

    assert "recent_turns" in captured
    assert len(captured["recent_turns"]) == 1
    assert captured["recent_turns"][0]["turn_number"] == 1
    assert "filled_gaps" in captured
    assert len(captured["filled_gaps"]) == 1
    assert captured["filled_gaps"][0]["gap_id"] == "gd"
    assert "open_gaps" in captured
    assert len(captured["open_gaps"]) == 1
    assert captured["open_gaps"][0]["gap_id"] == "go"


@pytest.mark.asyncio
async def test_generate_response_filters_every_turn() -> None:
    """Defensive filter runs even when the LLM repeats prior wording."""
    filled = InformationGap(
        gap_id="gd",
        category="business_context",
        description="business goals and stakeholders",
        priority="critical",
        filled=True,
        filled_in_turn=1,
    )
    state = WorkshopContext(session_id="s", user_id="u", current_turn=2)
    state.gaps = [filled]

    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "acknowledgement": "ok",
            "progress_note": "",
            "questions": [
                {"question": "What are the business goals and stakeholders?"},
            ],
        })
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "x"}}

    with patch(
        "app.workshop.nodes.load_prompt",
        return_value="prompt",
    ):
        out = await generate_response_node(state, config)

    assert out.turns
    assert "business goals" not in out.turns[-1].agent_response.lower()
