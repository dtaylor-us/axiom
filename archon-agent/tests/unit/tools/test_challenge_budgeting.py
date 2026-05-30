"""Tests for requirement challenge context budgeting."""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.models import ArchitectureContext
from app.tools.challenge_engine import RequirementChallengeEngineTool


@pytest.fixture
def context_with_many_requirements(base_context: ArchitectureContext) -> ArchitectureContext:
    """Return a context with enough parsed requirement lists to budget."""
    base_context.parsed_entities = {
        "domain": "fintech",
        "system_type": "payment platform",
        "functional_requirements": [{"id": "F1"}, {"id": "F2"}],
        "non_functional_requirements": [{"id": "N1"}],
        "constraints": [{"id": "C1"}],
    }
    return base_context


@pytest.fixture
def challenge_response() -> str:
    """Return a valid empty challenge response."""
    return json.dumps({
        "missing_requirements": [],
        "ambiguities": [],
        "hidden_assumptions": [],
        "clarifying_questions": [],
        "architecture_override": {
            "type": "none",
            "styles": [],
            "raw_instruction": "",
            "detected_confidence": "low",
        },
        "buy_vs_build_preferences": {
            "prefer_open_source": False,
            "avoid_vendor_lockin": False,
            "existing_tools": [],
            "build_preference": "neutral",
            "budget_constrained": False,
            "raw_signals": [],
        },
    })


@pytest.mark.asyncio
async def test_challenge_engine_budgets_requirements_before_building_prompt(
    context_with_many_requirements: ArchitectureContext,
    challenge_response: str,
) -> None:
    """Requirement challenge passes budgeted entities into the prompt."""
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=challenge_response)
    captured_kwargs = {}

    def capture_prompt(template_name: str, **kwargs: object) -> str:
        captured_kwargs.update(kwargs)
        return "prompt"

    with patch("app.tools.challenge_engine.load_prompt", side_effect=capture_prompt):
        with patch(
            "app.tools.challenge_engine.budget_json_list",
            return_value=[{"field_name": "functional_requirements", "item": {"id": "F1"}}],
        ):
            await RequirementChallengeEngineTool(llm).run(context_with_many_requirements)

    parsed_entities = captured_kwargs["parsed_entities"]
    assert parsed_entities["functional_requirements"] == [{"id": "F1"}]
    assert parsed_entities["non_functional_requirements"] == []


@pytest.mark.asyncio
async def test_challenge_engine_prioritises_functional_over_non_functional(
    context_with_many_requirements: ArchitectureContext,
    challenge_response: str,
) -> None:
    """Budget ordering puts functional requirements before non-functional ones."""
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=challenge_response)
    ordered_items: list[dict] = []

    def capture_budget(items: list[dict], **kwargs: object) -> list[dict]:
        ordered_items.extend(items)
        return items

    with patch("app.tools.challenge_engine.load_prompt", return_value="prompt"):
        with patch(
            "app.tools.challenge_engine.budget_json_list",
            side_effect=capture_budget,
        ):
            await RequirementChallengeEngineTool(llm).run(context_with_many_requirements)

    assert ordered_items[0]["field_name"] == "functional_requirements"
    assert ordered_items[1]["field_name"] == "functional_requirements"
    assert ordered_items[2]["field_name"] == "non_functional_requirements"


@pytest.mark.asyncio
async def test_challenge_engine_logs_when_requirements_are_truncated(
    context_with_many_requirements: ArchitectureContext,
    challenge_response: str,
    caplog,
) -> None:
    """Requirement challenge logs when budgeting drops parsed requirements."""
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=challenge_response)

    with patch("app.tools.challenge_engine.load_prompt", return_value="prompt"):
        with patch(
            "app.tools.challenge_engine.budget_json_list",
            return_value=[{"field_name": "functional_requirements", "item": {"id": "F1"}}],
        ):
            with caplog.at_level(logging.INFO):
                await RequirementChallengeEngineTool(llm).run(
                    context_with_many_requirements
                )

    assert "budgeted 1 of 4 requirements" in caplog.text


@pytest.mark.asyncio
async def test_challenge_engine_uses_requirement_challenge_schema_name(
    context_with_many_requirements: ArchitectureContext,
    challenge_response: str,
) -> None:
    """Requirement challenge passes the stage name as schema_name."""
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value=challenge_response)

    with patch("app.tools.challenge_engine.load_prompt", return_value="prompt"):
        await RequirementChallengeEngineTool(llm).run(context_with_many_requirements)

    kwargs = llm.complete.call_args.kwargs
    assert kwargs["schema_name"] == "requirement_challenge"
    assert kwargs["schema_name"] != "tool_output"
