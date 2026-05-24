from __future__ import annotations

import json
import logging

import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.base import ToolExecutionException
from app.tools.buy_vs_build_analyzer import BuyVsBuildAnalyzerTool


def _context_with_design() -> ArchitectureContext:
    ctx = ArchitectureContext(raw_requirements="test")
    ctx.parsed_entities = {"domain": "fintech", "system_type": "payments"}
    ctx.characteristics = [{"name": "scalability"}]
    ctx.scenarios = [{"tier": "medium", "description": "5k TPS"}]
    ctx.buy_vs_build_preferences = {
        "prefer_open_source": False,
        "avoid_vendor_lockin": False,
        "existing_tools": [],
        "build_preference": "neutral",
        "budget_constrained": False,
        "raw_signals": [],
    }
    ctx.architecture_design = {
        "style": "Event-driven",
        "components": [
            {"name": "Payments", "type": "service"},
            {"name": "Identity", "type": "service"},
            {"name": "ExternalBilling", "type": "external"},
        ],
    }
    return ctx


VALID_DECISION = {
    "component_name": "Identity",
    "recommendation": "adopt",
    "rationale": "Adopt Keycloak to avoid building OAuth/SAML flows; team capacity is limited but OSS is acceptable here.",
    "alternatives_considered": ["Keycloak", "Auth0", "Okta"],
    "recommended_solution": "Keycloak 24.x (self-hosted)",
    "estimated_build_cost": "free, ~$200/month infra",
    "vendor_lock_in_risk": "low",
    "integration_effort": "medium",
    "conflicts_with_user_preference": False,
    "conflict_explanation": "",
    "is_core_differentiator": False,
}


class TestBuyVsBuildAnalyzerTool:
    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> BuyVsBuildAnalyzerTool:
        return BuyVsBuildAnalyzerTool(mock_llm)

    async def test_run_derives_candidates_when_architecture_design_empty(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock,
    ):
        ctx = ArchitectureContext(raw_requirements="needs payment and email")
        ctx.architecture_design = {}
        mock_llm.complete.return_value = json.dumps({
            "decisions": [VALID_DECISION],
            "buy_vs_build_summary": "ok",
        })

        await tool.run(ctx)

        prompt_arg = mock_llm.complete.call_args.args[0]
        assert "Payment Provider" in prompt_arg
        assert "Email Delivery" in prompt_arg

    async def test_run_raises_when_components_list_empty(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        ctx = ArchitectureContext(raw_requirements="x")
        ctx.architecture_design = {"style": "Layered", "components": []}

        with pytest.raises(ToolExecutionException, match="candidate capabilities"):
            await tool.run(ctx)

    async def test_run_skips_components_with_type_external(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock,
    ):
        ctx = _context_with_design()

        mock_llm.complete.return_value = json.dumps({
            "decisions": [VALID_DECISION],
            "buy_vs_build_summary": "ok",
        })

        await tool.run(ctx)

        prompt_arg = mock_llm.complete.call_args.args[0]
        assert "ExternalBilling" not in prompt_arg

    async def test_run_falls_back_to_all_non_external_when_no_expected_types(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock,
    ):
        ctx = _context_with_design()
        ctx.architecture_design["components"] = [
            {"name": "CoreSystem", "type": "core-system"},
            {"name": "Worker", "type": "processing-unit"},
            {"name": "ExternalBilling", "type": "external"},
        ]

        mock_llm.complete.return_value = json.dumps({
            "decisions": [VALID_DECISION],
            "buy_vs_build_summary": "ok",
        })

        await tool.run(ctx)

        prompt_arg = mock_llm.complete.call_args.args[0]
        assert "CoreSystem" in prompt_arg
        assert "Worker" in prompt_arg
        assert "ExternalBilling" not in prompt_arg

    async def test_run_calls_llm_client_complete_with_response_format_json(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock,
    ):
        ctx = _context_with_design()
        mock_llm.complete.return_value = json.dumps({
            "decisions": [VALID_DECISION],
            "buy_vs_build_summary": "ok",
        })

        await tool.run(ctx)

        mock_llm.complete.assert_awaited_once()
        assert mock_llm.complete.call_args.kwargs["response_format"] == "json"

    async def test_run_writes_buy_vs_build_analysis_list_to_context(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock,
    ):
        ctx = _context_with_design()
        mock_llm.complete.return_value = json.dumps({
            "decisions": [VALID_DECISION],
            "buy_vs_build_summary": "ok",
        })

        result = await tool.run(ctx)

        assert len(result.buy_vs_build_analysis) == 1
        assert result.buy_vs_build_analysis[0]["component_name"] == "Identity"

    async def test_run_writes_buy_vs_build_summary_string_to_context(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock,
    ):
        ctx = _context_with_design()
        mock_llm.complete.return_value = json.dumps({
            "decisions": [VALID_DECISION],
            "buy_vs_build_summary": "Summary paragraph.",
        })

        result = await tool.run(ctx)

        assert result.buy_vs_build_summary == "Summary paragraph."

    async def test_run_raises_when_llm_returns_invalid_json(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock,
    ):
        ctx = _context_with_design()
        mock_llm.complete.return_value = "not json"

        with pytest.raises(ToolExecutionException, match="repair attempt"):
            await tool.run(ctx)

    async def test_run_logs_warning_for_each_rejected_decision(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock, caplog,
    ):
        ctx = _context_with_design()
        invalid = dict(VALID_DECISION)
        invalid["rationale"] = "short"

        mock_llm.complete.return_value = json.dumps({
            "decisions": [invalid],
            "buy_vs_build_summary": "ok",
        })

        with caplog.at_level(logging.WARNING):
            result = await tool.run(ctx)

        assert result.buy_vs_build_analysis == []
        assert any("Rejected buy-vs-build decision" in r.message for r in caplog.records)

    async def test_validate_decision_returns_none_for_valid_dict(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        assert tool._validate_decision(dict(VALID_DECISION)) is None

    async def test_validate_decision_returns_reason_when_recommendation_invalid(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        raw = dict(VALID_DECISION)
        raw["recommendation"] = "make"
        assert "recommendation" in (tool._validate_decision(raw) or "")

    async def test_validate_decision_returns_reason_when_rationale_too_short(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        raw = dict(VALID_DECISION)
        raw["rationale"] = "x" * 10
        assert "rationale" in (tool._validate_decision(raw) or "")

    async def test_validate_decision_returns_reason_when_alternatives_too_few(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        raw = dict(VALID_DECISION)
        raw["alternatives_considered"] = ["Keycloak"]
        assert "alternatives_considered" in (tool._validate_decision(raw) or "")

    async def test_validate_decision_returns_reason_when_buy_missing_recommended_solution(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        raw = dict(VALID_DECISION)
        raw["recommendation"] = "buy"
        raw["recommended_solution"] = ""
        assert "recommended_solution" in (tool._validate_decision(raw) or "")

    async def test_validate_decision_returns_reason_when_vendor_lock_in_risk_invalid(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        raw = dict(VALID_DECISION)
        raw["vendor_lock_in_risk"] = "extreme"
        assert "vendor_lock_in_risk" in (tool._validate_decision(raw) or "")

    async def test_validate_decision_returns_reason_when_conflict_true_but_explanation_empty(
        self, tool: BuyVsBuildAnalyzerTool,
    ):
        raw = dict(VALID_DECISION)
        raw["conflicts_with_user_preference"] = True
        raw["conflict_explanation"] = ""
        assert "conflict_explanation" in (tool._validate_decision(raw) or "")

    async def test_run_logs_info_with_build_buy_adopt_counts(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock, caplog,
    ):
        ctx = _context_with_design()

        build = dict(VALID_DECISION)
        build["component_name"] = "Payments"
        build["recommendation"] = "build"
        build["recommended_solution"] = ""

        buy = dict(VALID_DECISION)
        buy["component_name"] = "Email"
        buy["recommendation"] = "buy"
        buy["recommended_solution"] = "SendGrid"
        buy["vendor_lock_in_risk"] = "medium"
        buy["integration_effort"] = "low"

        adopt = dict(VALID_DECISION)
        adopt["component_name"] = "Search"
        adopt["recommendation"] = "adopt"
        adopt["recommended_solution"] = "OpenSearch"

        mock_llm.complete.return_value = json.dumps({
            "decisions": [build, buy, adopt],
            "buy_vs_build_summary": "ok",
        })

        with caplog.at_level(logging.INFO):
            await tool.run(ctx)

        assert any("BUY_VS_BUILD: analysis complete" in r.message for r in caplog.records)

    async def test_run_logs_warning_when_zero_decisions_returned(
        self, tool: BuyVsBuildAnalyzerTool, mock_llm: AsyncMock, caplog,
    ):
        ctx = _context_with_design()
        mock_llm.complete.return_value = json.dumps({
            "decisions": [],
            "buy_vs_build_summary": "none",
        })

        with caplog.at_level(logging.WARNING):
            result = await tool.run(ctx)

        assert result.buy_vs_build_analysis == []
        assert any("BUY_VS_BUILD: returned zero decisions" in r.message for r in caplog.records)

    async def test_canonical_decisions_returns_empty_when_no_buy_or_adopt_exist(self):
        ctx = ArchitectureContext()
        build = dict(VALID_DECISION)
        build["recommendation"] = "build"
        build["recommended_solution"] = ""
        ctx.buy_vs_build_analysis = [build]

        assert ctx.canonical_decisions == []

    async def test_canonical_decisions_returns_entries_for_buy(self):
        ctx = ArchitectureContext()
        buy = dict(VALID_DECISION)
        buy["recommendation"] = "buy"
        buy["recommended_solution"] = "Auth0"
        ctx.buy_vs_build_analysis = [buy]

        result = ctx.canonical_decisions

        assert len(result) == 1
        assert result[0]["component"] == "Identity"
        assert result[0]["decision"] == "buy"
        assert "EXTERNAL" in result[0]["constraint"]

    async def test_canonical_decisions_logs_each_component_evaluated(self, caplog):
        ctx = ArchitectureContext()
        ctx.buy_vs_build_analysis = [dict(VALID_DECISION)]

        with caplog.at_level(logging.DEBUG):
            _ = ctx.canonical_decisions

        assert any("CANONICAL_DECISIONS: evaluating component=Identity" in r.message for r in caplog.records)
