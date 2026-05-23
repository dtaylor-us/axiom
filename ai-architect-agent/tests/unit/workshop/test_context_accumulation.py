"""Tests for prior-facts wiring and recent-turn windows in workshop prompts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.workshop.context import WorkshopContext, WorkshopTurn
from app.workshop.nodes import analyze_input_node, generate_response_node


@pytest.mark.asyncio
async def test_analyze_input_passes_prior_known_facts_to_prompt() -> None:
    captured: dict = {}

    def fake_load(name: str, **kwargs: object) -> str:
        captured.update(kwargs)
        return '{"system_name":"","extracted_facts":[]}'

    state = WorkshopContext(session_id="s", user_id="u")
    state.system_name = "Claims Portal"
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value='{"system_name":"","extracted_facts":[]}')
    config = {"configurable": {"llm_client": llm, "latest_input": "more detail"}}

    with patch("app.workshop.nodes.load_prompt", side_effect=fake_load):
        await analyze_input_node(state, config)

    assert "prior_known_facts" in captured
    assert any(
        "Claims Portal" in str(f.get("fact", ""))
        for f in captured["prior_known_facts"]
    )


@pytest.mark.asyncio
async def test_analyze_input_turn_one_empty_prior_facts() -> None:
    captured: dict = {}

    def fake_load(name: str, **kwargs: object) -> str:
        captured.update(kwargs)
        return '{"system_name":"","extracted_facts":[]}'

    state = WorkshopContext(session_id="s", user_id="u")
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value='{"system_name":"","extracted_facts":[]}')
    config = {"configurable": {"llm_client": llm, "latest_input": "hello"}}

    with patch("app.workshop.nodes.load_prompt", side_effect=fake_load):
        await analyze_input_node(state, config)

    assert captured.get("prior_known_facts") == []


@pytest.mark.asyncio
async def test_generate_response_turn_three_includes_prior_turns_in_window() -> None:
    turns = [
        WorkshopTurn(
            turn_number=n,
            user_input=f"msg{n}",
            agent_response="",
            workshop_phase="business_context",
        )
        for n in range(1, 3)
    ]
    state = WorkshopContext(session_id="s", user_id="u", current_turn=3)
    state.turns = turns
    state.gaps = []

    captured: dict = {}

    def fake_load(name: str, **kwargs: object) -> str:
        captured.update(kwargs)
        return "{}"

    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value='{"acknowledgement":"","progress_note":"","questions":[]}'
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "t3"}}

    with patch("app.workshop.nodes.load_prompt", side_effect=fake_load):
        await generate_response_node(state, config)

    rt = captured.get("recent_turns", [])
    assert len(rt) == 2
    assert {x["turn_number"] for x in rt} == {1, 2}


@pytest.mark.asyncio
async def test_three_turn_simulation_filtered_duplicate_no_repeat_in_output() -> None:
    """
    When the facilitator LLM echoes a question similar to turn 1, the safety
    net removes it so the user does not see a repeated question.
    """
    state = WorkshopContext(session_id="s", user_id="u", current_turn=3)
    state.turns = [
        WorkshopTurn(
            turn_number=1,
            user_input="We need 99.9% uptime for payments.",
            agent_response="",
            questions_asked=["What availability target applies to payments?"],
            workshop_phase="risk_priority",
        ),
        WorkshopTurn(
            turn_number=2,
            user_input="PCI applies to card data only.",
            agent_response="",
            questions_asked=["Which components fall under PCI scope?"],
            workshop_phase="risk_priority",
        ),
    ]
    state.gaps = []

    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=(
            '{"acknowledgement":"ok","progress_note":"","questions":['
            '{"question":"What availability target applies to payments?",'
            '"gap_id":"","rationale":""}]}'
        )
    )
    config = {"configurable": {"llm_client": llm, "latest_input": "third"}}

    with patch("app.workshop.nodes.load_prompt", return_value="p"):
        out = await generate_response_node(state, config)

    assert out.turns[-1].questions_asked == []
