"""LangGraph pipeline assembly for SpecWeaver extraction."""

from __future__ import annotations

import logging
import os
from typing import Any

from langgraph.graph import END, StateGraph

from app.pipeline.context import SpecWeaverContext
from app.tools.classification_tool import ClassificationTool
from app.tools.conflict_detection_tool import ConflictDetectionTool
from app.tools.consolidation_tool import ConsolidationTool
from app.tools.extraction_tool import ExtractionTool
from app.tools.gap_analysis_tool import GapAnalysisTool
from app.tools.output_formatter import OutputFormatterTool

logger = logging.getLogger(__name__)


def check_extraction_results(context: SpecWeaverContext) -> SpecWeaverContext:
    """Abort when extraction produced no requirements from non-empty inputs.

    This guard prevents malformed extraction output from being silently wrapped
    into a successful empty package.

    Args:
        context: Current pipeline context.

    Returns:
        The unchanged context when extraction produced usable output.

    Raises:
        ValueError: If all documents failed and no requirements were extracted.
    """
    total_extracted = sum(
        len(result.extracted_requirements)
        for result in context.extraction_results
    )

    if total_extracted == 0 and context.documents:
        failed_documents = [
            error for error in context.pipeline_errors
            if "Extraction failed" in error
        ]
        raise ValueError(
            "Extraction produced zero requirements from "
            f"{len(context.documents)} document(s). "
            f"Pipeline errors: {failed_documents}. "
            "This is likely caused by malformed or truncated LLM JSON output."
        )

    partial_failures = [
        error for error in context.pipeline_errors
        if "Extraction failed" in error
    ]
    if partial_failures:
        logger.warning(
            "extraction_guard: partial extraction failure documents=%d "
            "requirements=%d session=%s",
            len(partial_failures),
            total_extracted,
            context.session_id,
        )

    return context


def build_graph(llm_client, qdrant_url: str | None = None) -> StateGraph:
    """
    Build the Phase 1b SpecWeaver extraction pipeline.

    The pipeline extracts, consolidates, classifies, analyzes gaps and conflicts,
    then formats the deterministic ArchInputPackage shell.
    """
    resolved_qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://qdrant:6333")
    extraction = ExtractionTool(llm_client)
    consolidation = ConsolidationTool(llm_client, resolved_qdrant_url)
    classification = ClassificationTool(llm_client)
    gap_analysis = GapAnalysisTool(llm_client)
    conflict_detection = ConflictDetectionTool(llm_client)
    formatter = OutputFormatterTool(llm_client)

    graph = StateGraph(SpecWeaverContext)

    graph.add_node("extraction", _node(extraction))
    graph.add_node("extraction_guard", check_extraction_results)
    graph.add_node("consolidation", _node(consolidation))
    graph.add_node("classification", _node(classification))
    graph.add_node("gap_analysis", _node(gap_analysis))
    graph.add_node("conflict_detection", _node(conflict_detection))
    graph.add_node("output_formatting", _node(formatter))

    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "extraction_guard")
    graph.add_edge("extraction_guard", "consolidation")
    graph.add_edge("consolidation", "classification")
    graph.add_edge("classification", "gap_analysis")
    graph.add_edge("gap_analysis", "conflict_detection")
    graph.add_edge("conflict_detection", "output_formatting")
    graph.add_edge("output_formatting", END)

    compiled_graph = graph.compile()
    logger.info("Pipeline graph compiled with 7 stages")
    return compiled_graph


def coerce_context(value: Any) -> SpecWeaverContext:
    """Coerce LangGraph state into a SpecWeaverContext instance."""
    if isinstance(value, SpecWeaverContext):
        return value
    if isinstance(value, dict):
        return SpecWeaverContext(**value)
    raise TypeError(f"Unsupported SpecWeaverContext state: {type(value)!r}")


def _node(tool):
    async def run_node(state: SpecWeaverContext | dict) -> SpecWeaverContext:
        context = coerce_context(state)
        return await tool.execute(context)

    return run_node
