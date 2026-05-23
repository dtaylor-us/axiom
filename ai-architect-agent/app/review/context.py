"""Review context models used by the ArchitectReviewAgent sub-graph.

These models are internal to the review agent. The main pipeline
communicates with the review agent through ArchitectureContext fields.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Leaf models ──────────────────────────────────────────────────


class AssumptionChallenge(BaseModel):
    """A challenged assumption found during review."""

    assumption: str
    risk: str
    recommendation: str


class TradeOffChallenge(BaseModel):
    """A trade-off decision challenged during review."""

    decision_id: str
    concern: str
    suggested_revision: str
    severity: str = "medium"  # low | medium | high


class AdlIssue(BaseModel):
    """An issue found during ADL audit."""

    adl_id: str
    issue_type: str          # missing_coverage | weak_assertion | contradiction
    description: str
    recommendation: str


class ImprovementRecommendation(BaseModel):
    """A specific improvement the review agent recommends."""

    area: str
    recommendation: str
    priority: str = "medium"  # low | medium | high
    requires_reiteration: bool = False


class GovernanceScoreBreakdown(BaseModel):
    """Detailed breakdown of the governance score."""

    requirement_coverage: int = 0       # 0-25
    architectural_soundness: int = 0    # 0-25
    risk_mitigation: int = 0            # 0-25
    governance_completeness: int = 0    # 0-25
    total: int = 0                      # 0-100
    justification: str = ""


# ── Review agent state ───────────────────────────────────────────

class SubReviewResult(BaseModel):
    """Records the outcome of one review sub-stage.

    Populated by each review node regardless of success or failure.
    """

    node_name: str
    # One of: challenge_assumptions, stress_test_trade_offs,
    #         audit_adl, score_governance
    succeeded: bool
    failure_reason: str = ""
    # Non-empty only when succeeded is False
    items_produced: int = 0
    # Count of findings produced (challenges, issues, recommendations)


class ReviewContext(BaseModel):
    """State for the ArchitectReviewAgent sub-graph.

    Created as a deep copy of the main ArchitectureContext data —
    the review agent never holds a reference to the live context.
    """

    # Snapshot from main context — read-only references
    conversation_id: str = ""
    raw_requirements: str = ""
    parsed_entities: dict[str, Any] = Field(default_factory=dict)
    characteristics: list[dict] = Field(default_factory=list)
    architecture_design: dict[str, Any] = Field(default_factory=dict)
    architecture_style_scores: list[dict] = Field(default_factory=list)
    scenarios: list[dict] = Field(default_factory=list)
    trade_offs: list[dict] = Field(default_factory=list)
    adl_blocks: list[dict] = Field(default_factory=list)
    weaknesses: list[dict] = Field(default_factory=list)
    fmea_risks: list[dict] = Field(default_factory=list)

    # Review outputs — populated by review nodes
    assumption_challenges: list[AssumptionChallenge] = Field(
        default_factory=list
    )
    trade_off_challenges: list[TradeOffChallenge] = Field(
        default_factory=list
    )
    adl_issues: list[AdlIssue] = Field(default_factory=list)
    improvement_recommendations: list[ImprovementRecommendation] = Field(
        default_factory=list
    )
    governance_score_breakdown: GovernanceScoreBreakdown | None = None
    governance_score: int | None = None
    should_reiterate: bool = False

    # Review health tracking — populated by review nodes
    sub_review_results: list[SubReviewResult] = Field(default_factory=list)
    review_completed_fully: bool = False
    governance_score_confidence: Literal[
        "high", "partial", "low", "unavailable"
    ] = "unavailable"

    @property
    def failed_sub_reviews(self) -> list[str]:
        """Returns names of sub-reviews that failed."""
        return [r.node_name for r in self.sub_review_results if not r.succeeded]

    @property
    def succeeded_sub_reviews(self) -> list[str]:
        """Returns names of sub-reviews that succeeded."""
        return [r.node_name for r in self.sub_review_results if r.succeeded]

    model_config = {"extra": "allow"}
