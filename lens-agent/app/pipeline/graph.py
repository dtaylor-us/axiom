from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.models.contracts import ReviewContext
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


def build_graph():
    graph = StateGraph(ReviewContext)
    graph.add_node("evidence_parsing", evidence_parsing)
    graph.add_node("azure_waf_analysis", azure_waf_analysis)
    graph.add_node("atam_analysis", atam_analysis)
    graph.add_node("sei_analysis", sei_analysis)
    graph.add_node("structural_analysis", structural_analysis)
    graph.add_node("risk_identification", risk_identification)
    graph.add_node("recommendation_generation", recommendation_generation)
    graph.add_node("executive_summary", executive_summary)
    graph.add_node("report_assembly", report_assembly)
    graph.add_node("review_complete", review_complete)

    graph.set_entry_point("evidence_parsing")
    for current_stage, next_stage in zip(ORDERED_STAGES, ORDERED_STAGES[1:]):
        graph.add_edge(current_stage, next_stage)
    graph.add_edge("review_complete", END)
    return graph.compile()
