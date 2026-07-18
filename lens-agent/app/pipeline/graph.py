"""LangGraph pipeline graph for the Lens 10-stage review pipeline.

Uses a TypedDict state schema so LangGraph can merge node outputs
correctly. ReviewContext is converted to/from the state dict at the
pipeline boundary in routes.py.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.pipeline.nodes import (
    atam_analysis,
    azure_waf_analysis,
    evidence_parsing,
    executive_summary,
    recommendation_generation,
    report_assembly,
    review_complete,
    risk_identification,
    sei_analysis,
    structural_analysis,
)

ORDERED_STAGES = [
    "evidence_parsing",
    "azure_waf_analysis",
    "atam_analysis",
    "sei_analysis",
    "structural_analysis",
    "risk_identification",
    "recommendation_generation",
    "executive_summary",
    "report_assembly",
    "review_complete",
]


class ReviewState(TypedDict, total=False):
    """
    LangGraph state schema for the Lens review pipeline.

    All fields are optional (total=False) so nodes can return partial
    updates and LangGraph merges them into the accumulated state.
    """

    session_id: str
    system_description: str
    evidence: list[dict]
    project_memory_context: dict
    gap_questions: list[dict]
    gap_answers: list[dict]
    insufficient_info_gaps: list[str]
    parsed_evidence: dict
    azure_waf_scorecard: dict
    atam_analysis: dict
    sei_analysis: dict
    structural_analysis: dict
    risks: list
    recommendations: list
    executive_summary: str
    overall_rating: str
    review_report: dict
    completed_stages: list[str]
    pipeline_gaps: list[str]
    has_gaps: bool


def build_graph():
    """
    Compile the Lens review LangGraph pipeline.

    Returns:
        Compiled StateGraph ready for ainvoke.
    """
    graph = StateGraph(ReviewState)

    graph.add_node("evidence_parsing", _wrap(evidence_parsing))
    graph.add_node("azure_waf_analysis", _wrap(azure_waf_analysis))
    graph.add_node("atam_analysis", _wrap(atam_analysis))
    graph.add_node("sei_analysis", _wrap(sei_analysis))
    graph.add_node("structural_analysis", _wrap(structural_analysis))
    graph.add_node("risk_identification", _wrap(risk_identification))
    graph.add_node("recommendation_generation", _wrap(recommendation_generation))
    graph.add_node("executive_summary", _wrap(executive_summary))
    graph.add_node("report_assembly", _wrap(report_assembly))
    graph.add_node("review_complete", _wrap(review_complete))

    graph.set_entry_point("evidence_parsing")
    for current_stage, next_stage in zip(ORDERED_STAGES, ORDERED_STAGES[1:]):
        graph.add_edge(current_stage, next_stage)
    graph.add_edge("review_complete", END)

    return graph.compile()


def _wrap(node_fn):
    """
    Wrap a node function that accepts ReviewContext to work with
    the LangGraph ReviewState dict.

    Converts the incoming state dict to a ReviewContext, calls the
    node, then converts the result back to a dict for LangGraph.

    Args:
        node_fn: Async node function accepting ReviewContext.

    Returns:
        Async wrapper function accepting and returning ReviewState dict.
    """
    from app.models.contracts import ReviewContext

    async def wrapper(state: dict[str, Any]) -> dict[str, Any]:
        context = ReviewContext(
            session_id=state.get("session_id", ""),
            system_description=state.get("system_description", ""),
            evidence=state.get("evidence", []),
            project_memory_context=state.get("project_memory_context"),
            gap_questions=state.get("gap_questions", []),
            gap_answers=state.get("gap_answers", []),
            insufficient_info_gaps=state.get("insufficient_info_gaps", []),
            parsed_evidence=state.get("parsed_evidence", {}),
            azure_waf_scorecard=state.get("azure_waf_scorecard", {}),
            atam_analysis=state.get("atam_analysis", {}),
            sei_analysis=state.get("sei_analysis", {}),
            structural_analysis=state.get("structural_analysis", {}),
            risks=state.get("risks", []),
            recommendations=state.get("recommendations", []),
            executive_summary=state.get("executive_summary", ""),
            overall_rating=state.get("overall_rating", ""),
            review_report=state.get("review_report", {}),
            completed_stages=list(state.get("completed_stages", [])),
            pipeline_gaps=list(state.get("pipeline_gaps", [])),
            has_gaps=state.get("has_gaps", False),
        )
        updated_context = await node_fn(context)
        return {
            "session_id": updated_context.session_id,
            "system_description": updated_context.system_description,
            "evidence": updated_context.evidence,
            "project_memory_context": updated_context.project_memory_context,
            "gap_questions": updated_context.gap_questions,
            "gap_answers": updated_context.gap_answers,
            "insufficient_info_gaps": updated_context.insufficient_info_gaps,
            "parsed_evidence": updated_context.parsed_evidence,
            "azure_waf_scorecard": updated_context.azure_waf_scorecard,
            "atam_analysis": updated_context.atam_analysis,
            "sei_analysis": updated_context.sei_analysis,
            "structural_analysis": updated_context.structural_analysis,
            "risks": updated_context.risks,
            "recommendations": updated_context.recommendations,
            "executive_summary": updated_context.executive_summary,
            "overall_rating": updated_context.overall_rating,
            "review_report": updated_context.review_report,
            "completed_stages": updated_context.completed_stages,
            "pipeline_gaps": updated_context.pipeline_gaps,
            "has_gaps": updated_context.has_gaps,
        }

    wrapper.__name__ = node_fn.__name__
    return wrapper
