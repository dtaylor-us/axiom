from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.scenario_modeler import ScenarioModelerTool
from app.tools.base import ToolExecutionException


def _make_scenarios(count: int = 3) -> dict:
    """Build a valid scenario response with the given number of scenarios."""
    tiers = ["small", "medium", "large"]
    scenarios = []
    for i in range(count):
        scenarios.append({
            "tier": tiers[i] if i < len(tiers) else f"extra-{i}",
            "label": f"Tier {i}",
            "load_profile": {
                "concurrent_users": 100 * (10 ** i),
                "requests_per_second": 10 * (10 ** i),
                "data_volume_gb": 1 * (10 ** i),
                "peak_multiplier": 3,
            },
            "architecture_shape": "monolith" if i == 0 else "microservices",
            "key_components": ["api", "db"],
            "deployment_target": "single VM" if i == 0 else "k8s",
            "team_size": f"{i + 1}-{i + 3} engineers",
            "estimated_monthly_infra_cost_usd": f"${100 * (10 ** i)}",
            "what_you_skip_at_this_tier": ["caching"],
            "migration_triggers": ["TPS exceeds limit"] if i < 2 else [],
        })
    return {
        "scenarios": scenarios,
        "key_architectural_inflection_points": ["Move from monolith to microservices"],
    }


VALID_RESPONSE = json.dumps(_make_scenarios(3))


class TestScenarioModelerTool:
    """Tests for ScenarioModelerTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> ScenarioModelerTool:
        return ScenarioModelerTool(mock_llm)

    @pytest.fixture
    def context_with_entities(self, base_context: ArchitectureContext) -> ArchitectureContext:
        base_context.parsed_entities = {"domain": "fintech", "system_type": "payment platform"}
        return base_context

    async def test_writes_exactly_three_scenarios(
        self, tool: ScenarioModelerTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() writes exactly 3 scenarios to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        assert len(result.scenarios) == 3

    async def test_scenario_tiers_ordered(
        self, tool: ScenarioModelerTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() returns tiers in small, medium, large order."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(context_with_entities)

        tiers = [s["tier"] for s in result.scenarios]
        assert tiers == ["small", "medium", "large"]

    async def test_raises_on_invalid_json(
        self, tool: ScenarioModelerTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() raises ToolExecutionException when LLM returns invalid JSON."""
        mock_llm.complete.return_value = "garbage data"

        with pytest.raises(ToolExecutionException, match="invalid JSON"):
            await tool.run(context_with_entities)

    async def test_does_not_mutate_other_fields(
        self, tool: ScenarioModelerTool, context_with_entities: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() does not mutate other ArchitectureContext fields."""
        mock_llm.complete.return_value = VALID_RESPONSE
        original_missing = context_with_entities.missing_requirements.copy()
        original_parsed = context_with_entities.parsed_entities.copy()

        await tool.run(context_with_entities)

        assert context_with_entities.missing_requirements == original_missing
        assert context_with_entities.parsed_entities == original_parsed

    async def test_raises_when_parsed_entities_empty(
        self, tool: ScenarioModelerTool, base_context: ArchitectureContext,
    ):
        """run() raises ToolExecutionException when parsed_entities is empty."""
        base_context.parsed_entities = {}

        with pytest.raises(ToolExecutionException, match="parsed_entities is empty"):
            await tool.run(base_context)
