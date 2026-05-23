from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.requirement_parser import RequirementParserTool
from app.tools.base import ToolExecutionException


VALID_RESPONSE = json.dumps({
    "domain": "fintech",
    "system_type": "payment platform",
    "functional_requirements": [
        {"id": "FR-001", "description": "Process payments", "priority": "must"},
        {"id": "FR-002", "description": "Fraud detection", "priority": "must"},
    ],
    "constraints": [
        {"type": "regulatory", "description": "PCI-DSS Level 1"}
    ],
    "integration_points": [
        {"system": "Stripe", "direction": "outbound", "protocol": "REST"}
    ],
    "quality_signals": ["low latency", "high availability"],
    "ambiguous_terms": ["real-time"],
})


class TestRequirementParserTool:
    """Tests for RequirementParserTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> RequirementParserTool:
        return RequirementParserTool(mock_llm)

    async def test_writes_domain_and_system_type(
        self, tool: RequirementParserTool, base_context: ArchitectureContext, mock_llm: AsyncMock
    ):
        """run() writes domain and system_type to context.parsed_entities."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(base_context)

        assert result.parsed_entities["domain"] == "fintech"
        assert result.parsed_entities["system_type"] == "payment platform"

    async def test_writes_functional_requirements(
        self, tool: RequirementParserTool, base_context: ArchitectureContext, mock_llm: AsyncMock
    ):
        """run() writes functional_requirements list to context.parsed_entities."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(base_context)

        frs = result.parsed_entities["functional_requirements"]
        assert len(frs) == 2
        assert frs[0]["id"] == "FR-001"

    async def test_raises_on_invalid_json(
        self, tool: RequirementParserTool, base_context: ArchitectureContext, mock_llm: AsyncMock
    ):
        """run() raises ToolExecutionException when LLM returns invalid JSON."""
        mock_llm.complete.return_value = "This is not valid JSON {{"

        with pytest.raises(ToolExecutionException, match="repair attempt"):
            await tool.run(base_context)

    async def test_does_not_mutate_other_fields(
        self, tool: RequirementParserTool, base_context: ArchitectureContext, mock_llm: AsyncMock
    ):
        """run() does not mutate other ArchitectureContext fields."""
        mock_llm.complete.return_value = VALID_RESPONSE
        original_scenarios = base_context.scenarios.copy()
        original_missing = base_context.missing_requirements.copy()

        await tool.run(base_context)

        assert base_context.scenarios == original_scenarios
        assert base_context.missing_requirements == original_missing

    async def test_raises_when_raw_requirements_empty(
        self, tool: RequirementParserTool, mock_llm: AsyncMock
    ):
        """run() raises ToolExecutionException when raw_requirements is empty."""
        ctx = ArchitectureContext(raw_requirements="")

        with pytest.raises(ToolExecutionException, match="raw_requirements is empty"):
            await tool.run(ctx)
