from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.challenge_engine import RequirementChallengeEngineTool
from app.tools.base import ToolExecutionException


VALID_RESPONSE = json.dumps({
    "missing_requirements": [
        {
            "area": "authentication",
            "description": "No auth strategy specified",
            "impact_if_ignored": "Security vulnerability",
        }
    ],
    "ambiguities": [
        {
            "term": "real-time",
            "context": "real-time processing",
            "possible_interpretations": ["sub-second", "sub-100ms"],
        }
    ],
    "hidden_assumptions": [
        {
            "assumption": "Single region deployment",
            "risk_if_wrong": "Latency for global users",
        }
    ],
    "clarifying_questions": [
        {
            "question": "What is the expected peak TPS?",
            "references": "missing load profile",
            "blocks_decision": "capacity planning",
        },
        {
            "question": "Which currencies must be supported?",
            "references": "multi-currency requirement",
            "blocks_decision": "data model design",
        },
        {
            "question": "What is the SLA target?",
            "references": "availability requirement",
            "blocks_decision": "architecture tier selection",
        },
        {
            "question": "Who are the primary users?",
            "references": "user personas",
            "blocks_decision": "UX architecture",
        },
        {
            "question": "Is there a compliance audit requirement?",
            "references": "regulatory gap",
            "blocks_decision": "logging architecture",
        },
    ],
    "architecture_override": {
        "type": "pinned",
        "styles": ["event-driven"],
        "raw_instruction": "Use event-driven architecture.",
        "detected_confidence": "high",
    },
    "buy_vs_build_preferences": {
        "prefer_open_source": True,
        "avoid_vendor_lockin": True,
        "existing_tools": ["Datadog"],
        "build_preference": "adopt",
        "budget_constrained": True,
        "raw_signals": ["prefer OSS", "no vendor lock-in", "we already use Datadog"],
    },
})


class TestRequirementChallengeEngineTool:
    """Tests for RequirementChallengeEngineTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> RequirementChallengeEngineTool:
        return RequirementChallengeEngineTool(mock_llm)

    @pytest.fixture
    def context_with_entities(self, base_context: ArchitectureContext) -> ArchitectureContext:
        """Context with parsed_entities already populated."""
        base_context.parsed_entities = {"domain": "fintech", "system_type": "payment platform"}
        return base_context

    async def test_writes_missing_requirements(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() writes missing_requirements to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        assert len(result.missing_requirements) == 1
        assert result.missing_requirements[0]["area"] == "authentication"

    async def test_writes_clarifying_questions(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() writes clarifying_questions to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        assert len(result.clarifying_questions) == 5
        assert "TPS" in result.clarifying_questions[0]["question"]

    async def test_raises_on_invalid_json(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() raises ToolExecutionException on invalid JSON response."""
        mock_llm.complete.return_value = "not json"

        with pytest.raises(ToolExecutionException, match="invalid JSON"):
            await tool.run(context_with_entities)

    async def test_raises_when_parsed_entities_empty(
        self, tool: RequirementChallengeEngineTool, base_context: ArchitectureContext,
    ):
        """run() raises ToolExecutionException when parsed_entities is empty."""
        base_context.parsed_entities = {}

        with pytest.raises(ToolExecutionException, match="parsed_entities is empty"):
            await tool.run(base_context)

    async def test_writes_ambiguities_and_hidden_assumptions(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() populates ambiguities and hidden_assumptions on context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        assert len(result.ambiguities) == 1
        assert result.ambiguities[0]["term"] == "real-time"
        assert len(result.hidden_assumptions) == 1

    async def test_run_extracts_architecture_override_from_llm_response(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() extracts architecture_override from LLM response."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        assert result.architecture_override["type"] == "pinned"
        assert "event-driven" in result.architecture_override["styles"]

    async def test_run_extracts_buy_vs_build_preferences_from_llm_response(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() extracts buy_vs_build_preferences from LLM response."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        assert result.buy_vs_build_preferences["prefer_open_source"] is True
        assert result.buy_vs_build_preferences["budget_constrained"] is True

    async def test_run_sets_default_architecture_override_when_not_in_response(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() sets default architecture_override when absent."""
        response = json.loads(VALID_RESPONSE)
        del response["architecture_override"]
        mock_llm.complete.return_value = json.dumps(response)

        result = await tool.run(context_with_entities)

        assert result.architecture_override["type"] == "none"
        assert result.architecture_override["styles"] == []

    async def test_run_sets_default_buy_vs_build_preferences_when_not_in_response(
        self, tool: RequirementChallengeEngineTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() sets default buy_vs_build_preferences when absent."""
        response = json.loads(VALID_RESPONSE)
        del response["buy_vs_build_preferences"]
        mock_llm.complete.return_value = json.dumps(response)

        result = await tool.run(context_with_entities)

        assert result.buy_vs_build_preferences["build_preference"] == "neutral"
        assert result.buy_vs_build_preferences["existing_tools"] == []
