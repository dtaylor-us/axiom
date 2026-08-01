"""Tests for the SpecWeaver LangGraph pipeline."""

from __future__ import annotations

import pytest

from app.models.contracts import ArchInputPackage
from app.pipeline.context import SpecWeaverContext
from app.pipeline.graph import build_graph, coerce_context
from app.tools.classification_tool import ClassificationTool
from app.tools.conflict_detection_tool import ConflictDetectionTool
from app.tools.consolidation_tool import ConsolidationTool
from app.tools.extraction_tool import ExtractionTool
from app.tools.gap_analysis_tool import GapAnalysisTool
from app.tools.output_formatter import OutputFormatterTool


@pytest.mark.asyncio
async def test_graph_runs_extraction_before_classification(
    monkeypatch,
    context,
    extraction_result,
):
    order = []

    async def extraction_run(self, ctx):
        order.append("extraction")
        ctx.extraction_results = [extraction_result]
        return ctx

    async def classification_run(self, ctx):
        order.append("classification")
        return ctx

    async def consolidation_run(self, ctx):
        order.append("consolidation")
        return ctx

    async def gap_analysis_run(self, ctx):
        order.append("gap_analysis")
        return ctx

    async def conflict_detection_run(self, ctx):
        order.append("conflict_detection")
        return ctx

    async def formatter_run(self, ctx):
        order.append("output_formatting")
        return ctx

    monkeypatch.setattr(ExtractionTool, "run", extraction_run)
    monkeypatch.setattr(ConsolidationTool, "run", consolidation_run)
    monkeypatch.setattr(ClassificationTool, "run", classification_run)
    monkeypatch.setattr(GapAnalysisTool, "run", gap_analysis_run)
    monkeypatch.setattr(ConflictDetectionTool, "run", conflict_detection_run)
    monkeypatch.setattr(OutputFormatterTool, "run", formatter_run)
    await build_graph(object()).ainvoke(context)
    assert order == [
        "extraction",
        "consolidation",
        "classification",
        "gap_analysis",
        "conflict_detection",
        "output_formatting",
    ]


@pytest.mark.asyncio
async def test_graph_runs_classification_before_output_formatting(
    monkeypatch,
    context,
    extraction_result,
):
    order = []

    async def record(name):
        async def run(self, ctx):
            order.append(name)
            if name == "extraction":
                ctx.extraction_results = [extraction_result]
            return ctx

        return run

    monkeypatch.setattr(ExtractionTool, "run", await record("extraction"))
    monkeypatch.setattr(ConsolidationTool, "run", await record("consolidation"))
    monkeypatch.setattr(ClassificationTool, "run", await record("classification"))
    monkeypatch.setattr(GapAnalysisTool, "run", await record("gap_analysis"))
    monkeypatch.setattr(
        ConflictDetectionTool,
        "run",
        await record("conflict_detection"),
    )
    monkeypatch.setattr(OutputFormatterTool, "run", await record("output_formatting"))
    await build_graph(object()).ainvoke(context)
    assert order == [
        "extraction",
        "consolidation",
        "classification",
        "gap_analysis",
        "conflict_detection",
        "output_formatting",
    ]


@pytest.mark.asyncio
async def test_graph_produces_arch_input_package_when_all_stages_succeed(
    monkeypatch,
    context,
    classified_set,
):
    async def extraction_run(self, ctx):
        ctx.extraction_results = []
        ctx.documents = []
        return ctx

    async def classification_run(self, ctx):
        ctx.classified_requirements = classified_set
        return ctx

    async def passthrough_run(self, ctx):
        return ctx

    async def formatter_run(self, ctx):
        ctx.arch_input_package = ArchInputPackage(
            package_id="pkg-1",
            session_id=ctx.session_id,
            created_at="2026-05-30T00:00:00Z",
            system_description="A system.",
            requirements=classified_set.requirements,
            source_documents=[],
            total_requirements=1,
            high_confidence_count=1,
            inferred_count=0,
        )
        return ctx

    monkeypatch.setattr(ExtractionTool, "run", extraction_run)
    monkeypatch.setattr(ConsolidationTool, "run", passthrough_run)
    monkeypatch.setattr(ClassificationTool, "run", classification_run)
    monkeypatch.setattr(GapAnalysisTool, "run", passthrough_run)
    monkeypatch.setattr(ConflictDetectionTool, "run", passthrough_run)
    monkeypatch.setattr(OutputFormatterTool, "run", formatter_run)
    result = coerce_context(await build_graph(object()).ainvoke(context))
    assert result.arch_input_package is not None


@pytest.mark.asyncio
async def test_graph_records_errors_in_pipeline_errors_on_stage_failure(
    monkeypatch,
    context,
):
    async def extraction_run(self, ctx):
        ctx.pipeline_errors.append("Extraction failed for document doc-1: boom")
        ctx.documents = []
        return ctx

    async def passthrough_run(self, ctx):
        return ctx

    monkeypatch.setattr(ExtractionTool, "run", extraction_run)
    monkeypatch.setattr(ConsolidationTool, "run", passthrough_run)
    monkeypatch.setattr(ClassificationTool, "run", passthrough_run)
    monkeypatch.setattr(GapAnalysisTool, "run", passthrough_run)
    monkeypatch.setattr(ConflictDetectionTool, "run", passthrough_run)
    monkeypatch.setattr(OutputFormatterTool, "run", passthrough_run)
    result = coerce_context(await build_graph(object()).ainvoke(context))
    assert result.pipeline_errors


@pytest.mark.asyncio
async def test_graph_returns_context_even_when_extraction_partially_fails(
    monkeypatch,
    context,
):
    async def extraction_run(self, ctx):
        ctx.pipeline_errors.append("partial failure")
        ctx.extraction_results = []
        ctx.documents = []
        ctx.completed_stages.append("extraction")
        return ctx

    async def passthrough_run(self, ctx):
        return ctx

    monkeypatch.setattr(ExtractionTool, "run", extraction_run)
    monkeypatch.setattr(ConsolidationTool, "run", passthrough_run)
    monkeypatch.setattr(ClassificationTool, "run", passthrough_run)
    monkeypatch.setattr(GapAnalysisTool, "run", passthrough_run)
    monkeypatch.setattr(ConflictDetectionTool, "run", passthrough_run)
    monkeypatch.setattr(OutputFormatterTool, "run", passthrough_run)
    result = coerce_context(await build_graph(object()).ainvoke(context))
    assert isinstance(result, SpecWeaverContext)
    assert "partial failure" in result.pipeline_errors
