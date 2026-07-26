from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReviewContext:
    session_id: str
    system_description: str
    evidence: list[dict]
    project_memory_context: dict | None = None
    gap_questions: list[dict] = field(default_factory=list)
    gap_answers: list[dict] = field(default_factory=list)
    insufficient_info_gaps: list[str] = field(default_factory=list)
    parsed_evidence: dict = field(default_factory=dict)
    azure_waf_scorecard: dict = field(default_factory=dict)
    atam_analysis: dict = field(default_factory=dict)
    sei_analysis: dict = field(default_factory=dict)
    structural_analysis: dict = field(default_factory=dict)
    risks: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    executive_summary: str = ""
    overall_rating: str = ""
    review_report: dict = field(default_factory=dict)
    completed_stages: list[str] = field(default_factory=list)
    pipeline_gaps: list[str] = field(default_factory=list)
    has_gaps: bool = False
