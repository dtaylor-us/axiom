from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.weakness_analyzer import WeaknessAnalyzerTool
from app.tools.base import ToolExecutionException


VALID_RESPONSE = json.dumps({
    "weaknesses": [
        {
            "id": "W-001",
            "category": "fragility",
            "title": "Synchronous fraud check creates cascading timeout",
            "component_affected": "PaymentGateway → FraudEngine",
            "description": "If FraudEngine is slow, the entire payment path blocks",
            "severity": 4,
            "likelihood": 3,
            "effort_to_fix": "weeks",
            "early_warning_signals": ["FraudEngine p99 latency > 500ms"],
            "mitigation": "Add circuit breaker with fallback to allow-list",
            "linked_characteristic": "latency",
        },
        {
            "id": "W-002",
            "category": "scale_limit",
            "title": "EventBus single partition bottleneck",
            "component_affected": "EventBus",
            "description": "Single partition limits throughput to 1k msgs/sec",
            "severity": 5,
            "likelihood": 4,
            "effort_to_fix": "weeks",
            "early_warning_signals": ["Consumer lag > 10k messages"],
            "mitigation": "Partition by merchant_id to distribute load",
            "linked_characteristic": "scalability",
        },
        {
            "id": "W-003",
            "category": "redesign_point",
            "title": "Monolithic settlement engine",
            "component_affected": "SettlementEngine",
            "description": "Settlement logic will need extraction to its own service",
            "severity": 3,
            "likelihood": 4,
            "effort_to_fix": "months",
            "early_warning_signals": ["Settlement batch time exceeds 4 hours"],
            "mitigation": "Extract settlement into a separate bounded context",
            "linked_characteristic": "modularity",
        },
        {
            "id": "W-004",
            "category": "operational",
            "title": "No distributed tracing across async boundaries",
            "component_affected": "All async interactions",
            "description": "Trace context lost when crossing event bus boundaries",
            "severity": 3,
            "likelihood": 5,
            "effort_to_fix": "days",
            "early_warning_signals": ["Ops team unable to trace transactions end-to-end"],
            "mitigation": "Propagate W3C trace context headers in event metadata",
            "linked_characteristic": "observability",
        },
    ],
    "weakness_summary": "The most critical weaknesses are the EventBus partition bottleneck and the synchronous fraud check path. Address these before scaling beyond 5k TPS.",
    "most_critical": "W-002",
})


RESPONSE_WITH_INVALID_WEAKNESSES = json.dumps({
    "weaknesses": [
        {
            "id": "W-001",
            "category": "fragility",
            "title": "Valid weakness",
            "component_affected": "ServiceA",
            "description": "Some failure mode",
            "severity": 4,
            "likelihood": 3,
            "effort_to_fix": "weeks",
            "early_warning_signals": ["metric > threshold"],
            "mitigation": "fix something",
            "linked_characteristic": "latency",
        },
        {
            "id": "W-002",
            "category": "fragility",
            "title": "Invalid severity",
            "component_affected": "ServiceB",
            "description": "desc",
            "severity": 6,
            "likelihood": 3,
            "effort_to_fix": "weeks",
            "early_warning_signals": ["signal"],
            "mitigation": "fix",
            "linked_characteristic": "latency",
        },
        {
            "id": "W-003",
            "category": "fragility",
            "title": "Invalid likelihood",
            "component_affected": "ServiceC",
            "description": "desc",
            "severity": 3,
            "likelihood": 0,
            "effort_to_fix": "weeks",
            "early_warning_signals": ["signal"],
            "mitigation": "fix",
            "linked_characteristic": "latency",
        },
        {
            "id": "W-004",
            "category": "invalid_category",
            "title": "Bad category",
            "component_affected": "ServiceD",
            "description": "desc",
            "severity": 3,
            "likelihood": 3,
            "effort_to_fix": "weeks",
            "early_warning_signals": ["signal"],
            "mitigation": "fix",
            "linked_characteristic": "latency",
        },
        {
            "id": "W-005",
            "category": "fragility",
            "title": "Empty signals",
            "component_affected": "ServiceE",
            "description": "desc",
            "severity": 3,
            "likelihood": 3,
            "effort_to_fix": "weeks",
            "early_warning_signals": [],
            "mitigation": "fix",
            "linked_characteristic": "latency",
        },
    ],
    "weakness_summary": "Summary text",
    "most_critical": "W-001",
})


class TestWeaknessAnalyzerTool:
    """Tests for WeaknessAnalyzerTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> WeaknessAnalyzerTool:
        return WeaknessAnalyzerTool(mock_llm)

    @pytest.fixture
    def rich_context(self, base_context: ArchitectureContext) -> ArchitectureContext:
        """Context with architecture_design populated."""
        base_context.parsed_entities = {
            "domain": "fintech",
            "system_type": "payment platform",
        }
        base_context.architecture_design = {
            "style": "event-driven microservices",
            "components": [
                {"name": "PaymentGateway", "type": "service"},
                {"name": "FraudEngine", "type": "service"},
            ],
        }
        base_context.characteristics = [
            {"name": "scalability"},
            {"name": "latency"},
        ]
        base_context.scenarios = [
            {"tier": "large", "description": "50k TPS peak load"},
        ]
        base_context.trade_offs = [
            {"decision_id": "TD-001", "decision": "Use async messaging"},
        ]
        return base_context

    async def test_writes_weaknesses_to_context(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes validated weaknesses to context.weaknesses."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert len(result.weaknesses) == 4

    async def test_writes_weakness_summary_to_context(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes weakness_summary to context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert "EventBus partition bottleneck" in result.weakness_summary

    async def test_sorts_by_severity_plus_likelihood_descending(
        self, tool, rich_context, mock_llm,
    ):
        """run() sorts weaknesses by (severity + likelihood) descending."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        scores = [
            w["severity"] + w["likelihood"] for w in result.weaknesses
        ]
        assert scores == sorted(scores, reverse=True)

    async def test_raises_without_architecture_design(
        self, tool, base_context,
    ):
        """run() raises ToolExecutionException when architecture_design is empty."""
        with pytest.raises(ToolExecutionException, match="architecture design"):
            await tool.run(base_context)

    async def test_raises_on_invalid_json(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException on invalid JSON from LLM."""
        mock_llm.complete.return_value = "{{broken"

        with pytest.raises(ToolExecutionException, match="repair attempt"):
            await tool.run(rich_context)

    async def test_filters_weakness_with_invalid_severity(
        self, tool, rich_context, mock_llm,
    ):
        """run() excludes weaknesses with severity outside 1-5."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_WEAKNESSES

        result = await tool.run(rich_context)

        weakness_ids = [w["id"] for w in result.weaknesses]
        assert "W-002" not in weakness_ids

    async def test_filters_weakness_with_invalid_likelihood(
        self, tool, rich_context, mock_llm,
    ):
        """run() excludes weaknesses with likelihood outside 1-5."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_WEAKNESSES

        result = await tool.run(rich_context)

        weakness_ids = [w["id"] for w in result.weaknesses]
        assert "W-003" not in weakness_ids

    async def test_filters_weakness_with_invalid_category(
        self, tool, rich_context, mock_llm,
    ):
        """run() excludes weaknesses with invalid category."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_WEAKNESSES

        result = await tool.run(rich_context)

        weakness_ids = [w["id"] for w in result.weaknesses]
        assert "W-004" not in weakness_ids

    async def test_filters_weakness_with_empty_signals(
        self, tool, rich_context, mock_llm,
    ):
        """run() excludes weaknesses with empty early_warning_signals."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_WEAKNESSES

        result = await tool.run(rich_context)

        weakness_ids = [w["id"] for w in result.weaknesses]
        assert "W-005" not in weakness_ids

    async def test_only_valid_weakness_remains_after_filtering(
        self, tool, rich_context, mock_llm,
    ):
        """run() keeps only the valid weakness from mixed input."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_WEAKNESSES

        result = await tool.run(rich_context)

        assert len(result.weaknesses) == 1
        assert result.weaknesses[0]["id"] == "W-001"

    async def test_does_not_mutate_other_context_fields(
        self, tool, rich_context, mock_llm,
    ):
        """run() does not write to fields other than weaknesses and weakness_summary."""
        mock_llm.complete.return_value = VALID_RESPONSE
        original_design = rich_context.architecture_design.copy()

        result = await tool.run(rich_context)

        assert result.architecture_design == original_design
        assert result.trade_offs == rich_context.trade_offs
        assert result.adl_rules == []

    async def test_calls_llm_with_json_format(
        self, tool, rich_context, mock_llm,
    ):
        """run() calls LLM with response_format='json'."""
        mock_llm.complete.return_value = VALID_RESPONSE

        await tool.run(rich_context)

        mock_llm.complete.assert_awaited_once()
        call_kwargs = mock_llm.complete.call_args
        assert call_kwargs.kwargs.get("response_format") == "json" or \
               (len(call_kwargs.args) > 1 and call_kwargs.args[1] == "json")
