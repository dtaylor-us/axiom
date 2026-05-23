from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import ArchitectureContext
from app.tools.characteristic_reasoner import CharacteristicReasoningEngineTool
from app.tools.base import ToolExecutionException


VALID_RESPONSE = json.dumps({
    "characteristics": [
        {
            "name": "scalability",
            "justification": "10k TPS requires horizontal scaling",
            "measurable_target": "p99 < 200ms under 10k TPS",
            "current_requirement_coverage": "explicit",
            "tensions_with": ["cost-efficiency"],
        },
        {
            "name": "security",
            "justification": "PCI-DSS L1 mandates encryption and audit",
            "measurable_target": "Zero PCI violations per quarter",
            "current_requirement_coverage": "explicit",
            "tensions_with": ["latency"],
        },
        {
            "name": "availability",
            "justification": "Payment system must not go down",
            "measurable_target": "99.99% uptime",
            "current_requirement_coverage": "explicit",
            "tensions_with": ["cost-efficiency"],
        },
        {
            "name": "latency",
            "justification": "Sub-100ms fraud detection requirement",
            "measurable_target": "p99 < 100ms for fraud check",
            "current_requirement_coverage": "explicit",
            "tensions_with": ["security"],
        },
    ],
    "reasoning_summary": "This system is dominated by the tension between low-latency payment processing and comprehensive PCI-DSS security controls.",
})


class TestCharacteristicReasoningEngineTool:
    """Tests for CharacteristicReasoningEngineTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> CharacteristicReasoningEngineTool:
        return CharacteristicReasoningEngineTool(mock_llm)

    @pytest.fixture
    def context_with_entities(self, base_context: ArchitectureContext) -> ArchitectureContext:
        """Context with parsed_entities already populated."""
        base_context.parsed_entities = {
            "domain": "fintech",
            "system_type": "payment platform",
            "quality_signals": ["low latency", "high availability"],
        }
        base_context.scenarios = [
            {"tier": "medium", "description": "5k TPS normal load"}
        ]
        return base_context

    async def test_writes_characteristics(
        self, tool, context_with_entities, mock_llm,
    ):
        """run() writes characteristics list to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        assert len(result.characteristics) == 4
        assert result.characteristics[0]["name"] == "scalability"

    async def test_calls_llm_with_json_format(
        self, tool, context_with_entities, mock_llm,
    ):
        """run() calls LLM with response_format='json'."""
        mock_llm.complete.return_value = VALID_RESPONSE

        await tool.run(context_with_entities)

        mock_llm.complete.assert_awaited_once()
        _, kwargs = mock_llm.complete.call_args
        assert kwargs.get("response_format") == "json"

    async def test_raises_when_parsed_entities_empty(
        self, tool, mock_llm,
    ):
        """run() raises ToolExecutionException when parsed_entities is empty."""
        ctx = ArchitectureContext(raw_requirements="test")

        with pytest.raises(ToolExecutionException, match="parsed_entities is empty"):
            await tool.run(ctx)

    async def test_raises_on_invalid_json(
        self, tool, context_with_entities, mock_llm,
    ):
        """run() raises ToolExecutionException when LLM returns invalid JSON."""
        mock_llm.complete.return_value = "not valid json {{"

        with pytest.raises(ToolExecutionException, match="invalid JSON"):
            await tool.run(context_with_entities)

    async def test_raises_on_repeated_empty_characteristics(
        self, tool, context_with_entities, mock_llm,
    ):
        """run() raises when both LLM attempts return empty characteristics."""
        mock_llm.complete.return_value = json.dumps({"characteristics": []})

        with pytest.raises(ToolExecutionException, match="both attempts"):
            await tool.run(context_with_entities)

    async def test_does_not_mutate_other_fields(
        self, tool, context_with_entities, mock_llm,
    ):
        """run() does not mutate other ArchitectureContext fields."""
        mock_llm.complete.return_value = VALID_RESPONSE
        original_scenarios = context_with_entities.scenarios.copy()

        await tool.run(context_with_entities)

        assert context_with_entities.scenarios == original_scenarios
