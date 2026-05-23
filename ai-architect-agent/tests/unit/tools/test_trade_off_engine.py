from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.trade_off_engine import TradeOffEngineTool
from app.tools.base import ToolExecutionException


VALID_RESPONSE = json.dumps({
    "decisions": [
        {
            "decision_id": "TD-001",
            "decision": "Use async event-driven communication between PaymentGateway and FraudEngine",
            "options_considered": [
                {
                    "option": "Synchronous REST calls",
                    "rejected_because": "Would create cascading timeouts under peak load",
                }
            ],
            "optimises_characteristics": ["scalability", "latency"],
            "sacrifices_characteristics": ["consistency"],
            "acceptable_because": "Eventual consistency is acceptable for fraud scoring since the payment is held until scored",
            "context_dependency": "If regulatory requirements mandate synchronous fraud checks, this inverts",
            "recommendation": "Use async event-driven messaging for fraud scoring",
            "confidence": "high",
            "confidence_reason": "Well-established pattern for high-throughput financial systems",
        },
        {
            "decision_id": "TD-002",
            "decision": "Deploy FraudEngine as a separate service with its own data store",
            "options_considered": [
                {
                    "option": "Embed fraud logic in PaymentGateway",
                    "rejected_because": "Tight coupling prevents independent scaling of ML model",
                }
            ],
            "optimises_characteristics": ["deployability", "scalability"],
            "sacrifices_characteristics": ["simplicity"],
            "acceptable_because": "Team has microservices expertise and fraud model changes frequently",
            "context_dependency": "If the fraud model rarely changes and load is low, a monolith would be simpler",
            "recommendation": "Maintain FraudEngine as an independently deployable service",
            "confidence": "medium",
            "confidence_reason": "Depends on team size and operational maturity",
        },
    ],
    "dominant_tension": "Latency vs. consistency is the primary trade-off",
})


RESPONSE_WITH_INVALID_DECISIONS = json.dumps({
    "decisions": [
        {
            "decision_id": "TD-001",
            "decision": "Valid decision",
            "optimises_characteristics": ["latency"],
            "sacrifices_characteristics": ["security"],
            "confidence": "high",
            "confidence_reason": "reason",
        },
        {
            "decision_id": "TD-002",
            "decision": "Empty optimises",
            "optimises_characteristics": [],
            "sacrifices_characteristics": ["security"],
            "confidence": "high",
            "confidence_reason": "reason",
        },
        {
            "decision_id": "TD-003",
            "decision": "Empty sacrifices",
            "optimises_characteristics": ["latency"],
            "sacrifices_characteristics": [],
            "confidence": "high",
            "confidence_reason": "reason",
        },
        {
            "decision_id": "TD-004",
            "decision": "Invalid confidence",
            "optimises_characteristics": ["latency"],
            "sacrifices_characteristics": ["security"],
            "confidence": "maybe",
            "confidence_reason": "reason",
        },
    ],
    "dominant_tension": "some tension",
})


class TestTradeOffEngineTool:
    """Tests for TradeOffEngineTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> TradeOffEngineTool:
        return TradeOffEngineTool(mock_llm)

    @pytest.fixture
    def rich_context(self, base_context: ArchitectureContext) -> ArchitectureContext:
        """Context with architecture_design and characteristics populated."""
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
            {"name": "consistency"},
        ]
        base_context.characteristic_conflicts = [
            {"characteristic_a": "latency", "characteristic_b": "consistency"},
        ]
        base_context.scenarios = [
            {"tier": "medium", "description": "5k TPS normal load"},
        ]
        return base_context

    async def test_writes_trade_offs_to_context(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes validated decisions to context.trade_offs."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert len(result.trade_offs) == 2
        assert result.trade_offs[0]["decision_id"] == "TD-001"
        assert result.trade_offs[1]["decision_id"] == "TD-002"

    async def test_raises_without_architecture_design(
        self, tool, base_context,
    ):
        """run() raises ToolExecutionException when architecture_design is empty."""
        with pytest.raises(ToolExecutionException, match="architecture design"):
            await tool.run(base_context)

    async def test_raises_without_characteristics(
        self, tool, rich_context,
    ):
        """run() raises ToolExecutionException when characteristics is empty."""
        rich_context.characteristics = []

        with pytest.raises(ToolExecutionException, match="characteristics"):
            await tool.run(rich_context)

    async def test_raises_on_invalid_json(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException on invalid JSON from LLM."""
        mock_llm.complete.return_value = "not valid json{{"

        with pytest.raises(ToolExecutionException, match="repair attempt"):
            await tool.run(rich_context)

    async def test_filters_decisions_with_empty_optimises(
        self, tool, rich_context, mock_llm,
    ):
        """run() excludes decisions with empty optimises_characteristics."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_DECISIONS

        result = await tool.run(rich_context)

        decision_ids = [d["decision_id"] for d in result.trade_offs]
        assert "TD-002" not in decision_ids

    async def test_filters_decisions_with_empty_sacrifices(
        self, tool, rich_context, mock_llm,
    ):
        """run() excludes decisions with empty sacrifices_characteristics."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_DECISIONS

        result = await tool.run(rich_context)

        decision_ids = [d["decision_id"] for d in result.trade_offs]
        assert "TD-003" not in decision_ids

    async def test_filters_decisions_with_invalid_confidence(
        self, tool, rich_context, mock_llm,
    ):
        """run() excludes decisions with invalid confidence value."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_DECISIONS

        result = await tool.run(rich_context)

        decision_ids = [d["decision_id"] for d in result.trade_offs]
        assert "TD-004" not in decision_ids

    async def test_only_valid_decisions_remain_after_filtering(
        self, tool, rich_context, mock_llm,
    ):
        """run() keeps only the one valid decision from mixed input."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_DECISIONS

        result = await tool.run(rich_context)

        assert len(result.trade_offs) == 1
        assert result.trade_offs[0]["decision_id"] == "TD-001"

    async def test_does_not_mutate_other_context_fields(
        self, tool, rich_context, mock_llm,
    ):
        """run() does not write to fields other than trade_offs / trade_off_dominant_tension."""
        mock_llm.complete.return_value = VALID_RESPONSE
        original_design = rich_context.architecture_design.copy()

        result = await tool.run(rich_context)

        assert result.architecture_design == original_design
        assert result.adl_rules == []
        assert result.weaknesses == []

    async def test_writes_dominant_tension_to_context(
        self, tool, rich_context, mock_llm,
    ):
        """run() stores dominant_tension from LLM response on context."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert result.trade_off_dominant_tension == (
            "Latency vs. consistency is the primary trade-off"
        )

    async def test_dominant_tension_defaults_empty_when_missing(
        self, tool, rich_context, mock_llm,
    ):
        """run() sets empty string when LLM omits dominant_tension."""
        response = json.dumps({
            "decisions": [
                {
                    "decision_id": "TD-001",
                    "decision": "Use async",
                    "optimises_characteristics": ["latency"],
                    "sacrifices_characteristics": ["consistency"],
                    "confidence": "high",
                    "confidence_reason": "reason",
                },
            ],
        })
        mock_llm.complete.return_value = response

        result = await tool.run(rich_context)

        assert result.trade_off_dominant_tension == ""

    async def test_dominant_tension_handles_null_value(
        self, tool, rich_context, mock_llm,
    ):
        """run() handles null dominant_tension from LLM as empty string."""
        response = json.dumps({
            "decisions": [
                {
                    "decision_id": "TD-001",
                    "decision": "Use async",
                    "optimises_characteristics": ["latency"],
                    "sacrifices_characteristics": ["consistency"],
                    "confidence": "high",
                    "confidence_reason": "reason",
                },
            ],
            "dominant_tension": None,
        })
        mock_llm.complete.return_value = response

        result = await tool.run(rich_context)

        assert result.trade_off_dominant_tension == ""

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
