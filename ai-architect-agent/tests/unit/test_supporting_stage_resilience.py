"""Tests for supporting stage resilience in the pipeline graph.

Covers ADL-036: supporting stage failures record a gap and allow the pipeline
to continue; core stage failures abort with ERROR.
"""
from __future__ import annotations

import json
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.models import ArchitectureContext, PipelineMode
from app.pipeline import graph as pipeline_graph
from app.tools.base import ToolExecutionException


def _passthrough_node(name: str):
    """Return an async node function that passes state through unchanged."""
    async def _node(state: dict) -> dict:
        return state
    _node.__name__ = name
    return _node


def _failing_node(name: str, exc: Exception):
    """Return an async node function that raises the given exception."""
    async def _node(state: dict) -> dict:
        raise exc
    _node.__name__ = name
    return _node


async def _collect_chunks(ctx: ArchitectureContext) -> list[dict]:
    """Run the pipeline and return all NDJSON chunks as parsed dicts."""
    chunks = []
    async for raw in pipeline_graph.run_pipeline(ctx):
        if raw.startswith(":"):
            continue  # skip heartbeat comments
        try:
            chunks.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return chunks


@pytest.fixture
def ctx() -> ArchitectureContext:
    return ArchitectureContext(
        conversation_id="test-resilience",
        raw_requirements="Build a payment platform",
        mode=PipelineMode.AUTO,
    )


@pytest.fixture(autouse=True)
def _patch_compiled(monkeypatch):
    """Ensure the compiled graph sentinel is non-None so run_pipeline() proceeds."""
    monkeypatch.setattr(pipeline_graph, "_compiled", object())
    monkeypatch.setattr(pipeline_graph, "HEARTBEAT_INTERVAL_SECONDS", 9999)


@pytest.fixture
def _passthrough_all(monkeypatch):
    """Patch all node functions in _NODE_FN_MAP to pass state through."""
    passthrough_map = {
        name: _passthrough_node(name)
        for name in pipeline_graph.ORDERED_STAGES
    }
    monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", passthrough_map)
    return passthrough_map


class TestSupportingStageGap:
    """When a supporting stage fails, the pipeline continues with a gap."""

    @pytest.mark.asyncio
    async def test_supporting_stage_failure_yields_completed_with_gaps(
        self, ctx, monkeypatch, _passthrough_all
    ):
        """STAGE_COMPLETE with status='completed_with_gaps' is emitted for gap stage."""
        gap_stage = "scenario_modeling"  # supporting stage
        node_map = dict(_passthrough_all)
        node_map[gap_stage] = _failing_node(
            gap_stage, ToolExecutionException("scenario LLM failed")
        )
        monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", node_map)

        chunks = await _collect_chunks(ctx)
        stage_complete_types = [
            c for c in chunks
            if c.get("type") == "STAGE_COMPLETE" and c.get("stage") == gap_stage
        ]
        assert stage_complete_types, f"No STAGE_COMPLETE for {gap_stage}"
        payload = stage_complete_types[0].get("payload", {})
        assert payload.get("status") == "completed_with_gaps"

    @pytest.mark.asyncio
    async def test_pipeline_continues_after_supporting_stage_failure(
        self, ctx, monkeypatch, _passthrough_all
    ):
        """Stages after the gap stage still emit STAGE_COMPLETE."""
        gap_stage = "scenario_modeling"
        node_map = dict(_passthrough_all)
        node_map[gap_stage] = _failing_node(
            gap_stage, ToolExecutionException("scenario LLM failed")
        )
        monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", node_map)

        chunks = await _collect_chunks(ctx)
        stage_complete_stages = {
            c["stage"] for c in chunks if c.get("type") == "STAGE_COMPLETE"
        }
        # Stages after scenario_modeling must still have STAGE_COMPLETE events
        subsequent = pipeline_graph.ORDERED_STAGES[
            pipeline_graph.ORDERED_STAGES.index(gap_stage) + 1:
        ]
        for stage in subsequent[:3]:  # check at least next 3 stages
            assert stage in stage_complete_stages, (
                f"Stage '{stage}' should have emitted STAGE_COMPLETE after gap in '{gap_stage}'"
            )

    @pytest.mark.asyncio
    async def test_complete_payload_has_gaps_true_when_gap_occurred(
        self, ctx, monkeypatch, _passthrough_all
    ):
        """COMPLETE payload contains has_gaps=True and non-empty pipeline_gaps."""
        gap_stage = "trade_off_analysis"  # supporting stage
        node_map = dict(_passthrough_all)
        node_map[gap_stage] = _failing_node(
            gap_stage, ToolExecutionException("trade off LLM failed")
        )
        monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", node_map)

        chunks = await _collect_chunks(ctx)
        complete_chunks = [c for c in chunks if c.get("type") == "COMPLETE"]
        assert complete_chunks, "No COMPLETE event emitted"
        payload = complete_chunks[0].get("payload", {})
        assert payload.get("has_gaps") is True
        assert isinstance(payload.get("pipeline_gaps"), list)
        assert len(payload["pipeline_gaps"]) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_gaps_records_stage_name_and_error(
        self, ctx, monkeypatch, _passthrough_all
    ):
        """pipeline_gaps entries contain stage_name and error fields."""
        gap_stage = "weakness_analysis"
        error_msg = "weakness analyzer timed out"
        node_map = dict(_passthrough_all)
        node_map[gap_stage] = _failing_node(
            gap_stage, ToolExecutionException(error_msg)
        )
        monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", node_map)

        chunks = await _collect_chunks(ctx)
        complete_chunks = [c for c in chunks if c.get("type") == "COMPLETE"]
        payload = complete_chunks[0].get("payload", {})
        gaps = payload.get("pipeline_gaps", [])
        assert any(g.get("stage_name") == gap_stage for g in gaps)
        matching = next(g for g in gaps if g.get("stage_name") == gap_stage)
        assert error_msg[:100] in matching.get("error", "")


class TestCoreStageAbort:
    """When a core stage fails, the pipeline emits ERROR and halts."""

    @pytest.mark.asyncio
    async def test_core_stage_failure_emits_error(
        self, ctx, monkeypatch, _passthrough_all
    ):
        """ERROR event is emitted when a core stage raises ToolExecutionException."""
        core_stage = "requirement_parsing"
        node_map = dict(_passthrough_all)
        node_map[core_stage] = _failing_node(
            core_stage, ToolExecutionException("requirement parser exploded")
        )
        monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", node_map)

        chunks = await _collect_chunks(ctx)
        error_chunks = [c for c in chunks if c.get("type") == "ERROR"]
        assert error_chunks, "No ERROR event emitted for core stage failure"

    @pytest.mark.asyncio
    async def test_core_stage_failure_does_not_emit_complete(
        self, ctx, monkeypatch, _passthrough_all
    ):
        """No COMPLETE event is emitted after a core stage failure."""
        core_stage = "architecture_generation"
        node_map = dict(_passthrough_all)
        node_map[core_stage] = _failing_node(
            core_stage, ToolExecutionException("arch gen failed")
        )
        monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", node_map)

        chunks = await _collect_chunks(ctx)
        complete_chunks = [c for c in chunks if c.get("type") == "COMPLETE"]
        assert not complete_chunks, "COMPLETE must not be emitted after a core stage failure"

    @pytest.mark.asyncio
    async def test_core_stage_failure_stops_subsequent_stages(
        self, ctx, monkeypatch, _passthrough_all
    ):
        """No STAGE_START or STAGE_COMPLETE events appear for stages after the failing core stage."""
        core_stage = "characteristic_inference"
        core_idx = pipeline_graph.ORDERED_STAGES.index(core_stage)
        node_map = dict(_passthrough_all)
        node_map[core_stage] = _failing_node(
            core_stage, ToolExecutionException("char inference failed")
        )
        monkeypatch.setattr(pipeline_graph, "_NODE_FN_MAP", node_map)

        chunks = await _collect_chunks(ctx)
        completed_stages = {
            c["stage"]
            for c in chunks
            if c.get("type") == "STAGE_COMPLETE" and "stage" in c
        }
        stages_after_core = pipeline_graph.ORDERED_STAGES[core_idx + 1:]
        unexpected = completed_stages & set(stages_after_core)
        assert not unexpected, (
            f"Stages {unexpected} emitted STAGE_COMPLETE after core stage failure in '{core_stage}'"
        )
