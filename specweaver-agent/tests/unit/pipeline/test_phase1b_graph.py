"""Tests for Phase 1b graph order and formatter context propagation."""

from __future__ import annotations

import pytest

from app.models.contracts import (
    ConflictDetectionResult,
    ConflictItem,
    ConsolidationResult,
    GapAnalysisResult,
    GapArea,
    GapSeverity,
)
from app.pipeline.graph import build_graph
from app.tools.classification_tool import ClassificationTool
from app.tools.conflict_detection_tool import ConflictDetectionTool
from app.tools.consolidation_tool import ConsolidationTool
from app.tools.extraction_tool import ExtractionTool
from app.tools.gap_analysis_tool import GapAnalysisTool
from app.tools.output_formatter import OutputFormatterTool


@pytest.mark.asyncio
async def test_graph_includes_phase1b_stage_order(monkeypatch, context):
    """The graph should run Phase 1b stages in the required order."""
    order = []

    async def record(stage_name):
        async def run(self, ctx):
            order.append(stage_name)
            if stage_name == "extraction":
                ctx.documents = []
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

    assert order.index("consolidation") > order.index("extraction")
    assert order.index("gap_analysis") > order.index("classification")
    assert order.index("conflict_detection") > order.index("gap_analysis")


@pytest.mark.asyncio
async def test_output_formatter_receives_gap_results(
    context,
    llm_client,
    classified_set,
):
    """Formatter should populate gaps from gap_analysis_result."""
    context.classified_requirements = classified_set
    context.gap_analysis_result = GapAnalysisResult(
        session_id="session-1",
        gaps=[_gap()],
        gap_count=1,
        by_severity={"critical": 0, "high": 1, "medium": 0, "low": 0},
    )
    llm_client.complete.return_value = '{"system_description":"A system."}'

    result = await OutputFormatterTool(llm_client).run(context)

    assert result.arch_input_package.gaps == context.gap_analysis_result.gaps


@pytest.mark.asyncio
async def test_output_formatter_receives_conflict_results(
    context,
    llm_client,
    classified_set,
):
    """Formatter should populate conflicts from conflict_detection_result."""
    context.classified_requirements = classified_set
    context.conflict_detection_result = ConflictDetectionResult(
        session_id="session-1",
        conflicts=[_conflict()],
        conflict_count=1,
    )
    llm_client.complete.return_value = '{"system_description":"A system."}'

    result = await OutputFormatterTool(llm_client).run(context)

    assert (
        result.arch_input_package.conflicts
        == context.conflict_detection_result.conflicts
    )


@pytest.mark.asyncio
async def test_output_formatter_populates_phase1b_counts(
    context,
    llm_client,
    classified_set,
    extracted_requirement,
):
    """Formatter should populate duplicate, gap, and conflict counts."""
    context.classified_requirements = classified_set
    context.consolidation_result = ConsolidationResult(
        session_id="session-1",
        consolidated_groups=[],
        merged_requirements=[extracted_requirement],
        duplicate_count=2,
        original_count=3,
        consolidated_count=1,
    )
    context.gap_analysis_result = GapAnalysisResult(
        session_id="session-1",
        gaps=[_gap()],
        gap_count=1,
        by_severity={"critical": 0, "high": 1, "medium": 0, "low": 0},
    )
    context.conflict_detection_result = ConflictDetectionResult(
        session_id="session-1",
        conflicts=[_conflict()],
        conflict_count=1,
    )
    llm_client.complete.return_value = '{"system_description":"A system."}'

    result = await OutputFormatterTool(llm_client).run(context)

    assert result.arch_input_package.duplicate_count == 2
    assert result.arch_input_package.gap_count == 1
    assert result.arch_input_package.conflict_count == 1


def _gap() -> GapArea:
    """Build a representative gap."""
    return GapArea(
        gap_id="GAP-1",
        area="Performance requirements",
        severity=GapSeverity.HIGH,
        explanation="Performance targets are needed.",
        clarification_question="What are the latency targets?",
        affected_categories=["non_functional"],
    )


def _conflict() -> ConflictItem:
    """Build a representative conflict."""
    return ConflictItem(
        conflict_id="CON-1",
        requirement_ids=["REQ-1", "REQ-2"],
        description="Two database requirements conflict.",
        interpretations=["Use option A.", "Use option B."],
        clarification_question="Which database is authoritative?",
    )
