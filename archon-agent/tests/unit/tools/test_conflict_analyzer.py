from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.conflict_analyzer import CharacteristicConflictAnalyzerTool
from app.tools.base import ToolExecutionException


VALID_RESPONSE = json.dumps({
    "conflicts": [
        {
            "characteristic_a": "scalability",
            "characteristic_b": "cost-efficiency",
            "nature": "direct_conflict",
            "explanation": "Scaling to 10k TPS requires expensive infrastructure",
            "resolution_strategy": "Auto-scaling with cost ceiling alerts",
            "priority_recommendation": "Favour scalability — downtime costs more than infra",
        },
        {
            "characteristic_a": "latency",
            "characteristic_b": "security",
            "nature": "tension",
            "explanation": "Encryption adds latency to every request",
            "resolution_strategy": "Hardware-accelerated crypto at the gateway layer",
            "priority_recommendation": "Both are non-negotiable — invest in hardware",
        },
    ],
    "underrepresented": ["observability"],
    "overspecified": [],
    "tension_summary": "The primary trade-off is between transaction throughput and compliance overhead.",
})


class TestCharacteristicConflictAnalyzerTool:
    """Tests for CharacteristicConflictAnalyzerTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> CharacteristicConflictAnalyzerTool:
        return CharacteristicConflictAnalyzerTool(mock_llm)

    @pytest.fixture
    def context_with_chars(self, base_context: ArchitectureContext) -> ArchitectureContext:
        """Context with characteristics already populated."""
        base_context.parsed_entities = {
            "domain": "fintech",
            "system_type": "payment platform",
        }
        base_context.characteristics = [
            {"name": "scalability", "tensions_with": ["cost-efficiency"]},
            {"name": "latency", "tensions_with": ["security"]},
        ]
        return base_context

    async def test_writes_conflicts(self, tool, context_with_chars, mock_llm):
        """run() writes characteristic_conflicts to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_chars)

        assert len(result.characteristic_conflicts) == 2
        assert result.characteristic_conflicts[0]["characteristic_a"] == "scalability"

    async def test_writes_underrepresented(self, tool, context_with_chars, mock_llm):
        """run() writes underrepresented_characteristics to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_chars)

        assert result.underrepresented_characteristics == ["observability"]

    async def test_writes_overspecified(self, tool, context_with_chars, mock_llm):
        """run() writes overspecified_characteristics to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_chars)

        assert result.overspecified_characteristics == []

    async def test_writes_tension_summary(self, tool, context_with_chars, mock_llm):
        """run() writes tension_summary to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_chars)

        assert "trade-off" in result.tension_summary.lower()

    async def test_raises_when_characteristics_empty(self, tool, mock_llm):
        """run() raises ToolExecutionException when characteristics is empty."""
        ctx = ArchitectureContext(raw_requirements="test")

        with pytest.raises(ToolExecutionException, match="characteristics is empty"):
            await tool.run(ctx)

    async def test_raises_on_invalid_json(self, tool, context_with_chars, mock_llm):
        """run() raises ToolExecutionException on invalid JSON."""
        mock_llm.complete.return_value = "broken json"

        with pytest.raises(ToolExecutionException, match="invalid JSON"):
            await tool.run(context_with_chars)

    async def test_does_not_mutate_other_fields(self, tool, context_with_chars, mock_llm):
        """run() does not mutate other ArchitectureContext fields."""
        mock_llm.complete.return_value = VALID_RESPONSE
        original_chars = context_with_chars.characteristics.copy()

        await tool.run(context_with_chars)

        assert context_with_chars.characteristics == original_chars
