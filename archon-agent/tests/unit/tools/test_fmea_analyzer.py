from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.fmea_analyzer import FMEAPlusTool
from app.tools.base import ToolExecutionException


VALID_RESPONSE = json.dumps({
    "fmea_risks": [
        {
            "id": "FMEA-001",
            "failure_mode": "Payment gateway timeout under peak load",
            "component": "PaymentGateway",
            "cause": "Single-threaded connection pool",
            "effect": "Transactions fail during peak hours",
            "severity": 9,
            "occurrence": 5,
            "detection": 3,
            "rpn": 135,
            "current_controls": "Retry with exponential backoff",
            "recommended_action": "Increase pool size and add circuit breaker",
            "linked_weakness": "W-001",
            "linked_characteristic": "scalability",
        },
        {
            "id": "FMEA-002",
            "failure_mode": "Fraud engine cascading failure",
            "component": "FraudEngine",
            "cause": "Synchronous dependency on ML model service",
            "effect": "All payments blocked when model service is slow",
            "severity": 10,
            "occurrence": 4,
            "detection": 5,
            "rpn": 200,
            "current_controls": "Health checks every 30s",
            "recommended_action": "Add async fallback with rule-based detection",
            "linked_weakness": "W-002",
            "linked_characteristic": "latency",
        },
        {
            "id": "FMEA-003",
            "failure_mode": "Message queue partition imbalance",
            "component": "EventBus",
            "cause": "Uneven key distribution",
            "effect": "Hot partitions cause processing delays",
            "severity": 6,
            "occurrence": 3,
            "detection": 4,
            "rpn": 72,
            "current_controls": "Consumer lag monitoring",
            "recommended_action": "Implement consistent hashing",
            "linked_weakness": "W-003",
            "linked_characteristic": "scalability",
        },
    ],
})


RESPONSE_WITH_INVALID_ENTRIES = json.dumps({
    "fmea_risks": [
        {
            "id": "FMEA-001",
            "failure_mode": "Valid risk",
            "component": "ServiceA",
            "cause": "Some cause",
            "effect": "Some effect",
            "severity": 7,
            "occurrence": 3,
            "detection": 4,
            "rpn": 84,
            "current_controls": "Monitoring",
            "recommended_action": "Fix it",
            "linked_weakness": "W-001",
            "linked_characteristic": "latency",
        },
        {
            "id": "FMEA-002",
            "failure_mode": "Severity out of range",
            "component": "ServiceB",
            "cause": "cause",
            "effect": "effect",
            "severity": 11,
            "occurrence": 3,
            "detection": 4,
            "rpn": 132,
            "current_controls": "None",
            "recommended_action": "Fix",
            "linked_weakness": "",
            "linked_characteristic": "",
        },
        {
            "id": "FMEA-003",
            "failure_mode": "Occurrence zero",
            "component": "ServiceC",
            "cause": "cause",
            "effect": "effect",
            "severity": 5,
            "occurrence": 0,
            "detection": 3,
            "rpn": 0,
            "current_controls": "None",
            "recommended_action": "Fix",
            "linked_weakness": "",
            "linked_characteristic": "",
        },
        {
            "id": "FMEA-004",
            "failure_mode": "Detection out of range",
            "component": "ServiceD",
            "cause": "cause",
            "effect": "effect",
            "severity": 5,
            "occurrence": 3,
            "detection": 15,
            "rpn": 225,
            "current_controls": "None",
            "recommended_action": "Fix",
            "linked_weakness": "",
            "linked_characteristic": "",
        },
    ],
})


RESPONSE_WITH_WRONG_RPN = json.dumps({
    "fmea_risks": [
        {
            "id": "FMEA-001",
            "failure_mode": "Wrong RPN",
            "component": "ServiceA",
            "cause": "cause",
            "effect": "effect",
            "severity": 8,
            "occurrence": 5,
            "detection": 3,
            "rpn": 999,
            "current_controls": "None",
            "recommended_action": "Fix",
            "linked_weakness": "",
            "linked_characteristic": "",
        },
    ],
})


RESPONSE_WITH_CRITICAL_RISKS = json.dumps({
    "fmea_risks": [
        {
            "id": "FMEA-HIGH-RPN",
            "failure_mode": "High RPN",
            "component": "Core",
            "cause": "cause",
            "effect": "effect",
            "severity": 8,
            "occurrence": 5,
            "detection": 6,
            "rpn": 240,
            "current_controls": "None",
            "recommended_action": "Fix",
            "linked_weakness": "",
            "linked_characteristic": "",
        },
        {
            "id": "FMEA-HIGH-SEV",
            "failure_mode": "High severity",
            "component": "Core",
            "cause": "cause",
            "effect": "effect",
            "severity": 9,
            "occurrence": 1,
            "detection": 1,
            "rpn": 9,
            "current_controls": "None",
            "recommended_action": "Fix",
            "linked_weakness": "",
            "linked_characteristic": "",
        },
        {
            "id": "FMEA-LOW",
            "failure_mode": "Low risk",
            "component": "Core",
            "cause": "cause",
            "effect": "effect",
            "severity": 3,
            "occurrence": 2,
            "detection": 2,
            "rpn": 12,
            "current_controls": "None",
            "recommended_action": "Fix",
            "linked_weakness": "",
            "linked_characteristic": "",
        },
    ],
})


class TestFMEAPlusTool:
    """Tests for FMEAPlusTool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> FMEAPlusTool:
        return FMEAPlusTool(mock_llm)

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
                {"name": "EventBus", "type": "infrastructure"},
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
        base_context.weaknesses = [
            {"id": "W-001", "category": "fragility", "title": "Gateway timeout"},
        ]
        return base_context

    async def test_writes_fmea_risks_to_context(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes validated FMEA risks to context.fmea_risks."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert len(result.fmea_risks) == 3

    async def test_sorts_by_rpn_descending(
        self, tool, rich_context, mock_llm,
    ):
        """run() sorts risks by RPN descending."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        rpns = [r["rpn"] for r in result.fmea_risks]
        assert rpns == sorted(rpns, reverse=True)

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
        mock_llm.complete.return_value = "{{broken json"

        with pytest.raises(ToolExecutionException, match="repair attempt"):
            await tool.run(rich_context)

    async def test_filters_invalid_severity(
        self, tool, rich_context, mock_llm,
    ):
        """run() drops risks with severity outside 1-10."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_ENTRIES

        result = await tool.run(rich_context)

        risk_ids = [r["id"] for r in result.fmea_risks]
        assert "FMEA-002" not in risk_ids

    async def test_filters_invalid_occurrence(
        self, tool, rich_context, mock_llm,
    ):
        """run() drops risks with occurrence outside 1-10."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_ENTRIES

        result = await tool.run(rich_context)

        risk_ids = [r["id"] for r in result.fmea_risks]
        assert "FMEA-003" not in risk_ids

    async def test_filters_invalid_detection(
        self, tool, rich_context, mock_llm,
    ):
        """run() drops risks with detection outside 1-10."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_ENTRIES

        result = await tool.run(rich_context)

        risk_ids = [r["id"] for r in result.fmea_risks]
        assert "FMEA-004" not in risk_ids

    async def test_only_valid_risk_remains(
        self, tool, rich_context, mock_llm,
    ):
        """run() keeps only valid risks after filtering."""
        mock_llm.complete.return_value = RESPONSE_WITH_INVALID_ENTRIES

        result = await tool.run(rich_context)

        assert len(result.fmea_risks) == 1
        assert result.fmea_risks[0]["id"] == "FMEA-001"

    async def test_corrects_wrong_rpn(
        self, tool, rich_context, mock_llm,
    ):
        """run() recalculates RPN when S×O×D doesn't match."""
        mock_llm.complete.return_value = RESPONSE_WITH_WRONG_RPN

        result = await tool.run(rich_context)

        risk = result.fmea_risks[0]
        expected_rpn = risk["severity"] * risk["occurrence"] * risk["detection"]
        assert risk["rpn"] == expected_rpn
        assert risk["rpn"] == 8 * 5 * 3  # 120, not 999

    async def test_extracts_critical_risks_by_rpn(
        self, tool, rich_context, mock_llm,
    ):
        """run() marks risks with RPN >= 200 as critical."""
        mock_llm.complete.return_value = RESPONSE_WITH_CRITICAL_RISKS

        result = await tool.run(rich_context)

        assert "FMEA-HIGH-RPN" in result.fmea_critical_risks

    async def test_extracts_critical_risks_by_severity(
        self, tool, rich_context, mock_llm,
    ):
        """run() marks risks with severity >= 9 as critical."""
        mock_llm.complete.return_value = RESPONSE_WITH_CRITICAL_RISKS

        result = await tool.run(rich_context)

        assert "FMEA-HIGH-SEV" in result.fmea_critical_risks

    async def test_low_risk_not_marked_critical(
        self, tool, rich_context, mock_llm,
    ):
        """run() does not mark low-RPN/low-severity risks as critical."""
        mock_llm.complete.return_value = RESPONSE_WITH_CRITICAL_RISKS

        result = await tool.run(rich_context)

        assert "FMEA-LOW" not in result.fmea_critical_risks

    async def test_does_not_mutate_other_context_fields(
        self, tool, rich_context, mock_llm,
    ):
        """run() only writes to fmea_risks and fmea_critical_risks."""
        mock_llm.complete.return_value = VALID_RESPONSE
        original_design = rich_context.architecture_design.copy()
        original_weaknesses = rich_context.weaknesses.copy()

        result = await tool.run(rich_context)

        assert result.architecture_design == original_design
        assert result.weaknesses == original_weaknesses

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

    async def test_builds_prompt_with_non_empty_weaknesses_when_present(
        self, tool, rich_context, mock_llm, monkeypatch,
    ):
        """run() passes context.weaknesses into the prompt builder."""
        captured = {}

        def _fake_load_prompt(template_name: str, **kwargs):
            captured["template_name"] = template_name
            captured["weaknesses"] = kwargs.get("weaknesses")
            return "prompt"

        monkeypatch.setattr(
            "app.tools.fmea_analyzer.load_prompt",
            _fake_load_prompt,
        )
        mock_llm.complete.return_value = VALID_RESPONSE

        await tool.run(rich_context)

        assert captured["template_name"] == "fmea_analyzer"
        assert captured["weaknesses"] == rich_context.weaknesses

    async def test_weakness_context_can_be_empty_and_is_still_passed(
        self, tool, rich_context, mock_llm, monkeypatch,
    ):
        """run() always passes weaknesses (empty list is allowed)."""
        rich_context.weaknesses = []
        captured = {}

        def _fake_load_prompt(template_name: str, **kwargs):
            captured["weaknesses"] = kwargs.get("weaknesses")
            return "prompt"

        monkeypatch.setattr(
            "app.tools.fmea_analyzer.load_prompt",
            _fake_load_prompt,
        )
        mock_llm.complete.return_value = VALID_RESPONSE

        await tool.run(rich_context)

        assert captured["weaknesses"] == []
