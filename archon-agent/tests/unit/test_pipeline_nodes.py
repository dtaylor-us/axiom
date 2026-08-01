from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models import ArchitectureContext
from app.pipeline.nodes import (
    requirement_parsing,
    requirement_challenge,
    scenario_modeling,
    characteristic_inference,
    tactics_recommendation,
    conflict_analysis,
    architecture_generation,
    buy_vs_build_analysis,
    diagram_generation,
    trade_off_analysis,
    adl_generation,
    weakness_analysis,
    weakness_and_fmea,
    fmea_analysis,
    architecture_review,
    init_registry,
    init_review_agent,
    PipelineState,
    _stub_node,
    _challenge_style_selection,
)


@pytest.fixture(autouse=True)
def _setup_registry(mock_llm: AsyncMock):
    """Set up a mock registry for all tests.

    Each mock tool has both .execute() and .run() — nodes call .execute()
    which in production delegates to .run() via BaseTool. Here we wire
    .execute() to pass through to .run() so both can be asserted on.
    """
    def _make_tool():
        tool = AsyncMock()
        tool.run = AsyncMock(side_effect=lambda ctx: ctx)

        async def _exec(ctx, _t=tool):
            return await _t.run(ctx)

        tool.execute = AsyncMock(side_effect=_exec)
        return tool

    mock_parser = _make_tool()
    mock_challenge = _make_tool()
    mock_scenario = _make_tool()
    mock_char_reasoner = _make_tool()
    mock_conflict = _make_tool()
    mock_arch_gen = _make_tool()
    mock_bvb = _make_tool()
    mock_diagram = _make_tool()
    mock_trade_off = _make_tool()
    mock_adl = _make_tool()
    mock_weakness = _make_tool()
    mock_fmea = _make_tool()
    mock_tactics_advisor = _make_tool()

    registry = {
        "requirement_parser": mock_parser,
        "challenge_engine": mock_challenge,
        "scenario_modeler": mock_scenario,
        "characteristic_reasoner": mock_char_reasoner,
        "tactics_advisor": mock_tactics_advisor,
        "conflict_analyzer": mock_conflict,
        "architecture_generator": mock_arch_gen,
        "buy_vs_build_analyzer": mock_bvb,
        "diagram_generator": mock_diagram,
        "trade_off_engine": mock_trade_off,
        "adl_generator": mock_adl,
        "weakness_analyzer": mock_weakness,
        "fmea_analyzer": mock_fmea,
    }
    init_registry(registry)

    # Also set up a mock review agent
    mock_review = AsyncMock()
    mock_review.run = AsyncMock(side_effect=lambda ctx: ctx)
    init_review_agent(mock_review)

    return registry


class TestLiveNodes:
    """Tests for live pipeline nodes (backed by tool calls)."""

    async def test_parse_node_calls_requirement_parser(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """parse_node() calls RequirementParserTool.run() with the context."""
        state: PipelineState = {"context": base_context}

        await requirement_parsing(state)

        _setup_registry["requirement_parser"].execute.assert_awaited_once_with(base_context)

    async def test_challenge_node_calls_challenge_engine(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """challenge_node() calls RequirementChallengeEngineTool.run()."""
        state: PipelineState = {"context": base_context}

        await requirement_challenge(state)

        _setup_registry["challenge_engine"].execute.assert_awaited_once_with(base_context)

    async def test_scenarios_node_calls_scenario_modeler(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """scenarios_node() calls ScenarioModelerTool.run()."""
        state: PipelineState = {"context": base_context}

        await scenario_modeling(state)

        _setup_registry["scenario_modeler"].execute.assert_awaited_once_with(base_context)

    async def test_characteristic_inference_calls_reasoner(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """characteristic_inference() calls CharacteristicReasoningEngineTool.run()."""
        state: PipelineState = {"context": base_context}

        await characteristic_inference(state)

        _setup_registry["characteristic_reasoner"].execute.assert_awaited_once_with(base_context)

    async def test_conflict_analysis_calls_analyzer(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """conflict_analysis() calls CharacteristicConflictAnalyzerTool.run()."""
        state: PipelineState = {"context": base_context}

        await conflict_analysis(state)

        _setup_registry["conflict_analyzer"].execute.assert_awaited_once_with(base_context)

    async def test_architecture_generation_calls_generator(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """architecture_generation() calls ArchitectureGeneratorTool.run()."""
        state: PipelineState = {"context": base_context}

        await architecture_generation(state)

        _setup_registry["architecture_generator"].execute.assert_awaited_once_with(base_context)

    async def test_buy_vs_build_analysis_calls_analyzer(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """buy_vs_build_analysis() calls BuyVsBuildAnalyzerTool.run()."""
        state: PipelineState = {"context": base_context}

        await buy_vs_build_analysis(state)

        _setup_registry["buy_vs_build_analyzer"].execute.assert_awaited_once_with(base_context)

    async def test_buy_vs_build_analysis_returns_context_with_analysis(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """buy_vs_build_analysis() returns context with buy_vs_build_analysis written."""
        expected = [{"component_name": "Payments", "recommendation": "buy"}]

        async def _run_with_analysis(ctx):
            ctx.buy_vs_build_analysis = expected
            ctx.buy_vs_build_summary = "Summary."
            return ctx

        _setup_registry["buy_vs_build_analyzer"].run = AsyncMock(
            side_effect=_run_with_analysis
        )

        async def _exec(ctx):
            return await _setup_registry["buy_vs_build_analyzer"].run(ctx)

        _setup_registry["buy_vs_build_analyzer"].execute = AsyncMock(side_effect=_exec)

        state: PipelineState = {"context": base_context}
        result = await buy_vs_build_analysis(state)

        assert result["context"].buy_vs_build_analysis == expected
        assert result["context"].buy_vs_build_summary == "Summary."

    async def test_diagram_generation_calls_diagram_tool(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """diagram_generation() calls DiagramGeneratorTool.run()."""
        state: PipelineState = {"context": base_context}

        await diagram_generation(state)

        _setup_registry["diagram_generator"].execute.assert_awaited_once_with(base_context)

    async def test_trade_off_analysis_calls_trade_off_engine(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """trade_off_analysis() calls TradeOffEngineTool.run()."""
        state: PipelineState = {"context": base_context}

        await trade_off_analysis(state)

        _setup_registry["trade_off_engine"].execute.assert_awaited_once_with(base_context)

    async def test_adl_generation_calls_adl_generator(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """adl_generation() calls ADLGeneratorV2Tool.run()."""
        state: PipelineState = {"context": base_context}

        await adl_generation(state)

        _setup_registry["adl_generator"].execute.assert_awaited_once_with(base_context)

    async def test_weakness_analysis_calls_weakness_analyzer(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """weakness_analysis() calls WeaknessAnalyzerTool.run()."""
        state: PipelineState = {"context": base_context}

        await weakness_analysis(state)

        _setup_registry["weakness_analyzer"].execute.assert_awaited_once_with(base_context)

    async def test_tactics_recommendation_calls_tactics_advisor(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """tactics_recommendation() calls TacticsAdvisorTool.execute() with context."""
        state: PipelineState = {"context": base_context}

        await tactics_recommendation(state)

        _setup_registry["tactics_advisor"].execute.assert_awaited_once_with(base_context)

    async def test_tactics_recommendation_returns_updated_context(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """tactics_recommendation() returns dict with updated context containing tactics field."""
        expected_tactics = [{"tactic_name": "Circuit Breaker", "characteristic_name": "availability"}]

        async def _run_with_tactics(ctx):
            ctx.tactics = expected_tactics
            return ctx

        _setup_registry["tactics_advisor"].run = AsyncMock(side_effect=_run_with_tactics)

        async def _exec(ctx):
            return await _setup_registry["tactics_advisor"].run(ctx)

        _setup_registry["tactics_advisor"].execute = AsyncMock(side_effect=_exec)

        state: PipelineState = {"context": base_context}
        result = await tactics_recommendation(state)

        assert result["context"].tactics == expected_tactics


class TestFmeaAndReviewNodes:
    """Tests for fmea_analysis, weakness_and_fmea, and architecture_review nodes."""

    async def test_fmea_analysis_calls_fmea_analyzer(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """fmea_analysis() calls FMEAPlusTool.run()."""
        state: PipelineState = {"context": base_context}

        await fmea_analysis(state)

        _setup_registry["fmea_analyzer"].execute.assert_awaited_once_with(base_context)

    async def test_weakness_and_fmea_calls_both_tools(
        self, base_context: ArchitectureContext, _setup_registry: dict,
    ):
        """weakness_and_fmea() calls both weakness_analyzer and fmea_analyzer."""
        state: PipelineState = {"context": base_context}

        await weakness_and_fmea(state)

        _setup_registry["weakness_analyzer"].execute.assert_awaited_once()
        _setup_registry["fmea_analyzer"].execute.assert_awaited_once()

    async def test_architecture_review_returns_context(
        self, base_context: ArchitectureContext,
    ):
        """architecture_review() returns context in result dict."""
        state: PipelineState = {"context": base_context}

        result = await architecture_review(state)

        assert "context" in result

    async def test_architecture_review_skips_llm_when_no_review_agent(
        self, base_context: ArchitectureContext,
    ):
        """architecture_review() logs warning and skips LLM when agent is None."""
        init_review_agent(None)
        state: PipelineState = {"context": base_context}

        result = await architecture_review(state)

        assert "context" in result


class TestStubNode:
    """Tests for _stub_node pass-through."""

    async def test_stub_node_returns_same_context(
        self, base_context: ArchitectureContext,
    ):
        state: PipelineState = {"context": base_context}
        result = await _stub_node(state)
        assert result["context"] is base_context


class TestChallengeStyleSelection:
    """Tests for _challenge_style_selection deterministic logic."""

    def _ctx_with_design(self, style_scores, selected, chars=None, scenarios=None):
        ctx = ArchitectureContext(
            raw_requirements="test",
            architecture_design={
                "style_selection": {
                    "style_scores": style_scores,
                    "selected_style": selected,
                    "runner_up": "Event-Driven",
                }
            },
            characteristics=chars or [],
            scenarios=scenarios or [],
        )
        return ctx

    def test_no_style_data_produces_challenged(self):
        ctx = ArchitectureContext(raw_requirements="test")
        result = _challenge_style_selection(ctx)
        challenge = result.review_findings["style_selection_challenge"]
        assert challenge["challenged"] is True
        assert "missing" in challenge["reason"]

    def test_top_characteristic_mismatch_challenges(self):
        ctx = self._ctx_with_design(
            style_scores=[{
                "style": "Microservices",
                "driving_characteristics": ["scalability"],
            }],
            selected="Microservices",
            chars=[{"name": "availability"}, {"name": "scalability"}],
        )
        result = _challenge_style_selection(ctx)
        challenge = result.review_findings["style_selection_challenge"]
        assert challenge["challenged"] is True
        assert "availability" in challenge["reason"]

    def test_vetoed_without_reason_challenges(self):
        ctx = self._ctx_with_design(
            style_scores=[
                {"style": "Microservices", "driving_characteristics": ["availability"]},
                {"style": "Monolith", "vetoed": True, "veto_reason": None},
            ],
            selected="Microservices",
            chars=[{"name": "availability"}],
        )
        result = _challenge_style_selection(ctx)
        challenge = result.review_findings["style_selection_challenge"]
        assert challenge["challenged"] is True

    def test_large_scenario_with_monolithic_style_challenges(self):
        ctx = self._ctx_with_design(
            style_scores=[{
                "style": "Layered",
                "driving_characteristics": ["simplicity"],
            }],
            selected="Layered",
            chars=[{"name": "simplicity"}],
            scenarios=[{
                "tier": "large",
                "description": "10k concurrent users hitting checkout",
            }],
        )
        result = _challenge_style_selection(ctx)
        challenge = result.review_findings["style_selection_challenge"]
        assert challenge["challenged"] is True
        assert challenge["recommended_alternative"] == "Event-Driven"

    def test_well_formed_selection_not_challenged(self):
        ctx = self._ctx_with_design(
            style_scores=[{
                "style": "Microservices",
                "driving_characteristics": ["availability", "scalability"],
                "vetoed": False,
            }],
            selected="Microservices",
            chars=[{"name": "availability"}, {"name": "scalability"}],
        )
        result = _challenge_style_selection(ctx)
        challenge = result.review_findings["style_selection_challenge"]
        assert challenge["challenged"] is False
