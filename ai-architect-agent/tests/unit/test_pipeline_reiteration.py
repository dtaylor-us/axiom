from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext, PipelineMode
from app.pipeline.graph import run_pipeline, compile_pipeline, ORDERED_STAGES
from app.pipeline.nodes import init_registry, init_review_agent


@pytest.fixture
def mock_registry():
    """Create a mock tool registry where every tool returns context unchanged.

    Each mock wires .execute() → .run() to match the production
    BaseTool.execute() delegation pattern.
    """
    tools = {}
    for name in [
        "requirement_parser",
        "challenge_engine",
        "scenario_modeler",
        "characteristic_reasoner",
        "conflict_analyzer",
        "architecture_generator",
        "buy_vs_build_analyzer",
        "diagram_generator",
        "trade_off_engine",
        "adl_generator",
        "weakness_analyzer",
        "fmea_analyzer",
        "tactics_advisor",
    ]:
        tool = AsyncMock()
        tool.run = AsyncMock(side_effect=_mock_tool_run(name))

        async def _exec(ctx, _t=tool):
            return await _t.run(ctx)

        tool.execute = AsyncMock(side_effect=_exec)
        tools[name] = tool
    return tools


def _mock_tool_run(name: str):
    """Return a tool side effect that preserves pipeline prerequisites."""
    def _run(ctx: ArchitectureContext) -> ArchitectureContext:
        if name == "characteristic_reasoner":
            ctx.characteristics = [{"name": "availability"}]
        if name == "architecture_generator":
            ctx.architecture_design = {
                "style_selection": {"selected_style": "service-based"},
                "components": [],
                "interactions": [],
            }
        return ctx

    return _run


@pytest.fixture
def mock_review_agent():
    agent = AsyncMock()
    agent.run = AsyncMock(side_effect=lambda ctx: ctx)
    return agent


@pytest.fixture(autouse=True)
def setup_pipeline(mock_registry, mock_review_agent):
    """Set up registry and compile pipeline for each test."""
    init_registry(mock_registry)
    init_review_agent(mock_review_agent)
    compile_pipeline()
    yield


@pytest.fixture
def base_context():
    return ArchitectureContext(
        conversation_id="test-reiteration",
        raw_requirements="Build a payment system",
        mode=PipelineMode.AUTO,
        iteration=0,
    )


class TestPipelineOrdering:

    def test_ordered_stages_has_14_entries(self):
        """ORDERED_STAGES must have exactly 14 stages."""
        assert len(ORDERED_STAGES) == 14

    def test_weakness_and_fmea_are_separate_stages(self):
        """weakness_analysis and fmea_analysis run as separate stages;
        the merged weakness_and_fmea node must not appear in the ordered list."""
        assert "weakness_analysis" in ORDERED_STAGES
        assert "fmea_analysis" in ORDERED_STAGES
        assert "weakness_and_fmea" not in ORDERED_STAGES

    def test_architecture_review_is_final_stage(self):
        """architecture_review must be the last stage."""
        assert ORDERED_STAGES[-1] == "architecture_review"


class TestPipelineStreaming:

    async def test_emits_stage_events_for_all_stages(
        self, base_context, mock_registry,
    ):
        chunks = []
        async for chunk in run_pipeline(base_context):
            parsed = json.loads(chunk)
            chunks.append(parsed)

        stage_starts = [c for c in chunks if c["type"] == "STAGE_START"]
        stage_completes = [c for c in chunks if c["type"] == "STAGE_COMPLETE"]

        assert len(stage_starts) == 14
        assert len(stage_completes) == 14

    async def test_ends_with_complete_event(self, base_context):
        last_chunk = None
        async for chunk in run_pipeline(base_context):
            last_chunk = json.loads(chunk)

        assert last_chunk["type"] == "COMPLETE"
        assert last_chunk["conversationId"] == "test-reiteration"

    async def test_complete_includes_structured_output(self, base_context):
        chunks = []
        async for chunk in run_pipeline(base_context):
            chunks.append(json.loads(chunk))

        complete = next(c for c in chunks if c["type"] == "COMPLETE")
        assert "structured_output" in complete["payload"]

    async def test_complete_includes_iteration(self, base_context):
        chunks = []
        async for chunk in run_pipeline(base_context):
            chunks.append(json.loads(chunk))

        complete = next(c for c in chunks if c["type"] == "COMPLETE")
        assert "iteration" in complete["payload"]


class TestReiterationGate:

    async def test_reiteration_emits_re_iterate_event(
        self, base_context, mock_review_agent,
    ):
        """When review agent sets should_reiterate=True on iteration 0,
        a RE_ITERATE event is emitted."""
        def set_reiterate(ctx):
            ctx.should_reiterate = True
            ctx.governance_score = 45
            ctx.review_constraints = ["Add circuit breakers"]
            return ctx

        # First iteration: trigger reiteration
        # Second iteration: don't reiterate
        call_count = 0
        async def smart_review(ctx):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return set_reiterate(ctx)
            return ctx

        mock_review_agent.run = AsyncMock(side_effect=smart_review)

        chunks = []
        async for chunk in run_pipeline(base_context):
            chunks.append(json.loads(chunk))

        re_iterate_chunks = [c for c in chunks if c["type"] == "RE_ITERATE"]
        assert len(re_iterate_chunks) == 1
        assert re_iterate_chunks[0]["payload"]["governance_score"] == 45

    async def test_reiteration_increments_iteration(
        self, base_context, mock_review_agent,
    ):
        """Re-iteration increments context.iteration."""
        call_count = 0
        async def track_iteration(ctx):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                ctx.should_reiterate = True
                ctx.governance_score = 40
                return ctx
            return ctx

        mock_review_agent.run = AsyncMock(side_effect=track_iteration)

        async for _ in run_pipeline(base_context):
            pass

        # After reiteration, iteration should be 1
        assert base_context.iteration == 1

    async def test_no_reiteration_on_final_iteration(
        self, base_context, mock_review_agent,
    ):
        """No RE_ITERATE event when iteration >= 1."""
        base_context.iteration = 1

        async def always_reiterate(ctx):
            ctx.should_reiterate = True
            ctx.governance_score = 30
            return ctx

        mock_review_agent.run = AsyncMock(side_effect=always_reiterate)

        chunks = []
        async for chunk in run_pipeline(base_context):
            chunks.append(json.loads(chunk))

        re_iterate_chunks = [c for c in chunks if c["type"] == "RE_ITERATE"]
        assert len(re_iterate_chunks) == 0

    async def test_no_reiteration_when_score_is_fine(
        self, base_context, mock_review_agent,
    ):
        """No RE_ITERATE when should_reiterate is False."""
        async def happy_review(ctx):
            ctx.should_reiterate = False
            ctx.governance_score = 85
            return ctx

        mock_review_agent.run = AsyncMock(side_effect=happy_review)

        chunks = []
        async for chunk in run_pipeline(base_context):
            chunks.append(json.loads(chunk))

        re_iterate_chunks = [c for c in chunks if c["type"] == "RE_ITERATE"]
        assert len(re_iterate_chunks) == 0
        # Should end with COMPLETE
        assert chunks[-1]["type"] == "COMPLETE"

    async def test_reiteration_runs_all_stages_twice(
        self, base_context, mock_review_agent, mock_registry,
    ):
        """Re-iteration executes all stages again."""
        call_count = 0
        async def one_reiteration(ctx):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                ctx.should_reiterate = True
                ctx.governance_score = 40
                return ctx
            return ctx

        mock_review_agent.run = AsyncMock(side_effect=one_reiteration)

        chunks = []
        async for chunk in run_pipeline(base_context):
            chunks.append(json.loads(chunk))

        completes = [c for c in chunks if c["type"] == "STAGE_COMPLETE"]
        assert len(completes) == 28  # 14 stages × 2 iterations

    async def test_re_iterate_payload_includes_constraints(
        self, base_context, mock_review_agent,
    ):
        """RE_ITERATE payload includes review_constraints."""
        call_count = 0
        async def review_with_constraints(ctx):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                ctx.should_reiterate = True
                ctx.governance_score = 40
                ctx.review_constraints = ["Fix gateway timeout", "Add retry logic"]
                return ctx
            return ctx

        mock_review_agent.run = AsyncMock(side_effect=review_with_constraints)

        chunks = []
        async for chunk in run_pipeline(base_context):
            chunks.append(json.loads(chunk))

        re_iterate = next(c for c in chunks if c["type"] == "RE_ITERATE")
        assert len(re_iterate["payload"]["constraints"]) == 2
