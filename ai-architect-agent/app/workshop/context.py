"""
WorkshopContext — the conversation state for a Quality Attribute
Workshop session.

Unlike ArchitectureContext which flows through a linear pipeline,
WorkshopContext is a mutable conversation state that accumulates
across multiple user turns. Each turn adds evidence, fills gaps,
and incrementally refines quality attributes.

The context is serialised to JSON and persisted in the database
after each turn so the conversation can be resumed across sessions.

Design principle: the context tracks not just what is known but
what is missing and why. The gap inventory is as important as
the attribute inventory.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

ScenarioCompleteness = Literal[
    "complete", "partial", "needs_measure", "aspirational"
]


def compute_scenario_completeness(
    stimulus: str,
    environment: str,
    response: str,
    response_measure: str,
) -> ScenarioCompleteness:
    """
    Derive scenario completeness from field content only.

    Rules align with workshop governance: a scenario is never "complete"
    unless stimulus, response, and response_measure each meet minimum
    substance thresholds — independent of LLM self-classification.
    """
    st = stimulus.strip()
    env = environment.strip()
    resp = response.strip()
    meas = response_measure.strip()
    has_stimulus = len(st) >= 10
    has_environment = len(env) >= 10
    has_response = len(resp) >= 10
    has_measure = len(meas) >= 10
    populated = sum([
        has_stimulus, has_environment, has_response, has_measure,
    ])
    if populated == 0:
        return "aspirational"
    if has_measure and has_response and has_stimulus:
        return "complete"
    if has_response and has_stimulus and not has_measure:
        return "needs_measure"
    if populated >= 2:
        return "partial"
    return "aspirational"


class QAScenario(BaseModel):
    """
    A Quality Attribute scenario following the Bass/Clements/Kazman
    six-part structure from 'Software Architecture in Practice'
    4th ed. chapter 2.

    A quality attribute without a grounded scenario is an aspiration.
    The workshop does not produce final attributes without at least
    a partial scenario for each.
    """
    scenario_id: str
    stimulus: str = ""
    source: str = ""
    environment: str = ""
    artifact: str = ""
    response: str = ""
    response_measure: str = ""
    completeness: ScenarioCompleteness = "aspirational"
    # complete:      all six parts present and measurable
    # partial:       most parts present, response_measure weak
    # needs_measure: good scenario but no measurable response
    # aspirational:  user stated a desire without scenario grounding

    def compute_completeness(self) -> ScenarioCompleteness:
        """
        Computes completeness from field content, overriding any LLM label.

        Returns:
            One of the four completeness bands derived from stimulus,
            environment, response, and response_measure lengths.
        """
        return compute_scenario_completeness(
            self.stimulus,
            self.environment,
            self.response,
            self.response_measure,
        )

    def model_post_init(self, __context: Any) -> None:
        """Recompute completeness so empty scenarios cannot be marked complete."""
        self.completeness = self.compute_completeness()


class WorkshopScenario(BaseModel):
    """
    A QA scenario as a first-class workshop artifact.

    Richer than ``QAScenario`` — includes title and explicit linkage to
    attributes the scenario exercises. Primary elicitation output before
    attributes are inferred.
    """

    scenario_id: str
    title: str = ""
    stimulus: str = ""
    source: str = ""
    environment: str = ""
    artifact: str = ""
    response: str = ""
    response_measure: str = ""
    exercises_attributes: list[str] = Field(default_factory=list)
    evidence_quote: str = ""
    derived_in_turn: int = 0

    @computed_field
    @property
    def completeness(self) -> ScenarioCompleteness:
        """Completeness derived from content (never trusts upstream labels)."""
        return compute_scenario_completeness(
            self.stimulus,
            self.environment,
            self.response,
            self.response_measure,
        )


class ElicitedAttribute(BaseModel):
    """
    A quality attribute derived from workshop evidence.

    Attributes are not asserted by the system — they are elicited
    from user-provided evidence. The evidence_quotes field records
    the specific phrases from user input that support this attribute.

    Confidence reflects the quality of the evidence, not the
    importance of the attribute. Low confidence means more
    clarifying questions are needed, not that the attribute is
    unimportant.
    """
    attribute_id: str
    name: str
    # Canonical name: Availability, Performance, Security, etc.
    category: Literal[
        "availability", "performance", "security", "modifiability",
        "scalability", "testability", "deployability", "usability",
        "interoperability", "data_integrity", "auditability",
        "recoverability", "cost", "other"
    ]
    description: str
    # What this attribute means specifically for this system
    importance: Literal["critical", "high", "medium", "low"] = "medium"
    confidence: Literal["confirmed", "inferred", "tentative"] = "tentative"
    # confirmed:  user explicitly stated this matters
    # inferred:   derived from context with strong evidence
    # tentative:  possible based on limited evidence, needs validation
    evidence_quotes: list[str] = Field(default_factory=list)
    # Verbatim phrases from user input that support this attribute
    scenarios: list[QAScenario] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    # Questions still needed to fully ground this attribute
    derived_in_turn: int = 0
    # Which conversation turn produced this attribute
    first_generation_pass: int | None = None
    # Which user-triggered generation first created this attribute
    last_generation_pass: int | None = None
    # Most recent generation pass that updated this attribute
    would_improve_with: list[str] = Field(default_factory=list)
    # gap_ids that would improve this attribute if filled

    # --- Consolidation fields (set by ConsolidationEngine) ---
    canonical_name: str = ""
    # The canonical category name after alias resolution, e.g. "availability"
    classification: Literal[
        "canonical", "alias", "sub_attribute", "non_qa", "unknown"
    ] = "unknown"
    # canonical:     this attribute maps directly to a recognised QA category
    # alias:         this attribute was an alias and has been normalised
    # sub_attribute: this attribute is a concern under a broader canonical QA
    # non_qa:        this is a legitimate concern but not a measurable QA
    # unknown:       not yet classified by the consolidator
    parent_attribute: str = ""
    # attribute_id of the parent when classification == "sub_attribute"
    merged_into: str = ""
    # attribute_id this was merged into (empty if still active)
    sub_concerns: list[str] = Field(default_factory=list)
    # Free-text sub-concerns captured under this attribute (e.g. "backup" under recoverability)


class InformationGap(BaseModel):
    """
    A gap in the information needed to derive quality attributes.

    Gaps are categorised by the QAW framework categories:
    business context, usage context, technical context, and
    risk/priority context.

    Gaps are modelled as confidence-scored uncertainty windows, not
    binary checklists. Resolution closes when accumulated evidence
    crosses a priority-based threshold.
    """

    gap_id: str
    category: Literal[
        "business_context", "usage_context",
        "technical_context", "risk_priority"
    ]
    qa_domain: str = ""
    description: str
    questions: list[str] = Field(default_factory=list)
    priority: Literal["critical", "high", "medium", "low"] = "medium"

    resolution_confidence: float = 0.0
    resolution_threshold: float = 0.75
    resolution_evidence: list[str] = Field(default_factory=list)
    residual_question: str = ""
    filled_in_turn: int | None = None
    answer_confidence: str = "unanswered"

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_filled(cls, data: Any) -> Any:
        """Map legacy boolean ``filled`` to confidence for persisted JSON."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if out.pop("filled", None) is True:
            rc = float(out.get("resolution_confidence") or 0.0)
            out["resolution_confidence"] = max(rc, 1.0)
        return out

    @computed_field
    @property
    def filled(self) -> bool:
        """True when ``resolution_confidence`` meets the priority threshold."""
        threshold = (
            0.9 if self.priority == "critical" else
            0.75 if self.priority == "high" else
            0.6
        )
        return self.resolution_confidence >= threshold

    @property
    def is_substantially_answered(self) -> bool:
        """True when confidence is at least 0.5 (partial progress band)."""
        return self.resolution_confidence >= 0.5


class GapProgressSnapshot(BaseModel):
    """Aggregate gap progress for UI and diagnostics."""

    total_gaps: int = 0
    filled_gaps: int = 0
    open_gap_ids: list[str] = Field(default_factory=list)
    in_progress_count: int = 0
    depth_score: int = 0


class WorkshopTurn(BaseModel):
    """
    One exchange in the workshop conversation.
    Immutable once recorded — the conversation is append-only.
    """
    turn_number: int
    user_input: str
    agent_response: str
    gaps_identified: list[str] = Field(default_factory=list)
    # gap_ids identified or filled in this turn
    attributes_derived: list[str] = Field(default_factory=list)
    # attribute_ids derived or updated in this turn
    questions_asked: list[str] = Field(default_factory=list)
    # The specific questions posed to the user this turn
    workshop_phase: str = ""
    # Which QAW phase this turn belongs to
    timestamp: str = ""


class WorkshopContext(BaseModel):
    """
    The full state of a Quality Attribute Workshop session.

    Persisted after every turn. The conversation can be resumed
    by loading this context from the database and continuing.

    The workshop_phase tracks where the session is in the QAW
    process. The agent uses this to know what to ask next.
    """
    session_id: str
    user_id: str
    system_name: str = ""
    # The name of the system being elicited for, if known

    # QAW phase tracking
    workshop_phase: Literal[
        "input_analysis",
        "business_context",
        "usage_context",
        "technical_context",
        "risk_priority",
        "scenario_brainstorm",
        "scenario_refinement",
        "attribute_consolidation",
        "validation",
        "complete"
    ] = "input_analysis"

    # Accumulated evidence across all turns
    raw_inputs: list[str] = Field(default_factory=list)
    # All user-provided text, accumulated across turns

    # Gap inventory
    gaps: list[InformationGap] = Field(default_factory=list)
    open_gaps: list[str] = Field(default_factory=list)
    # gap_ids not yet filled

    # Attribute inventory
    attributes: list[ElicitedAttribute] = Field(default_factory=list)
    confirmed_attributes: list[str] = Field(default_factory=list)
    # attribute_ids the user has confirmed as correct

    # Conversation history
    turns: list[WorkshopTurn] = Field(default_factory=list)
    current_turn: int = 0

    # Session metadata
    created_at: str = ""
    last_updated: str = ""
    is_complete: bool = False

    # Generation state — tracks whether attributes have been
    # generated and whether the session is in refinement mode
    generation_requested: bool = False
    # True once the user has explicitly requested generation
    # Can be requested multiple times — each request regenerates
    # from accumulated evidence

    generation_count: int = 0
    # How many times the user has triggered generation
    # Used to label attribute versions in the UI

    last_generation_turn: int | None = None
    # Which turn triggered the most recent generation
    # Attributes generated before this turn may be stale

    attributes_stale: bool = False
    # True when new evidence has been added after the last
    # generation — indicates the user should consider regenerating

    pre_generation_assessment: dict = Field(default_factory=dict)
    # Populated before each generation with an honest assessment
    # of what the current evidence supports:
    #   overall_readiness, confidence_note, attribute_preview,
    #   high_value_gaps, missing_domains, can_produce_useful_output

    # --- Consolidation tracking ---
    non_qa_concerns: list[dict] = Field(default_factory=list)
    # Concerns surfaced by the LLM that are not measurable quality attributes.
    # Each entry: {"name": str, "description": str, "captured_in_turn": int}
    last_consolidated_turn: int | None = None
    # Which turn most recently ran ConsolidationEngine.consolidate()

    # Primary workshop artifacts: scenarios accumulate first; attributes follow.
    scenarios: list[WorkshopScenario] = Field(default_factory=list)
    scenario_count_by_completeness: dict[str, int] = Field(default_factory=dict)

    @property
    def progress_snapshot(self) -> GapProgressSnapshot:
        """Gap progress including partially answered (in-progress) gaps."""
        open_gap_list = [g for g in self.gaps if not g.filled]
        closed_gap_list = [g for g in self.gaps if g.filled]
        in_progress = [
            g for g in open_gap_list
            if g.resolution_confidence >= 0.5
        ]
        if closed_gap_list:
            depth_score = int(sum(
                g.resolution_confidence * 100
                for g in closed_gap_list
            ) / len(closed_gap_list))
        else:
            depth_score = 0
        return GapProgressSnapshot(
            total_gaps=len(self.gaps),
            filled_gaps=len(closed_gap_list),
            open_gap_ids=[g.gap_id for g in open_gap_list],
            in_progress_count=len(in_progress),
            depth_score=depth_score,
        )

    def refresh_scenario_counts(self) -> WorkshopContext:
        """Recompute ``scenario_count_by_completeness`` from ``scenarios``."""
        counts: dict[str, int] = {
            "complete": 0,
            "needs_measure": 0,
            "partial": 0,
            "aspirational": 0,
        }
        for s in self.scenarios:
            key = s.completeness
            counts[key] = counts.get(key, 0) + 1
        return self.model_copy(update={
            "scenario_count_by_completeness": counts,
        })

    @property
    def can_generate(self) -> bool:
        """
        Returns True when there is sufficient evidence to attempt
        generation. The bar is intentionally low — one turn of
        input is enough to produce tentative attributes.
        The user decides whether tentative is sufficient.
        """
        return len(self.raw_inputs) >= 1 and len(self.turns) >= 1

    @property
    def generation_recommended(self) -> bool:
        """
        Returns True when the system judges the evidence is
        strong enough to produce at least 3 inferred or confirmed
        attributes. Used to show a suggestion in the UI, not to
        gate generation.
        """
        inferred_or_confirmed = sum(
            1 for a in self.attributes
            if a.confidence in ("confirmed", "inferred")
        )
        return inferred_or_confirmed >= 3 or self.filled_gaps >= 3

    @property
    def total_gaps(self) -> int:
        """Total number of information gaps identified so far."""
        return len(self.gaps)

    @property
    def filled_gaps(self) -> int:
        """Number of gaps that have been answered by the user."""
        return sum(1 for g in self.gaps if g.filled)

    @property
    def gap_completion_pct(self) -> int:
        """
        Percentage of identified gaps that are filled.

        Returns 0 when no gaps have been identified yet, avoiding
        a divide-by-zero condition at the start of the session.
        """
        if not self.gaps:
            return 0
        return int((self.filled_gaps / self.total_gaps) * 100)

    @property
    def confirmed_attribute_count(self) -> int:
        """Number of attributes the user has explicitly confirmed."""
        return len(self.confirmed_attributes)

    @property
    def has_sufficient_attributes(self) -> bool:
        """
        Returns True when the workshop has produced enough
        confirmed, grounded attributes to be useful output.
        Threshold: at least 3 confirmed attributes each with
        at least a partial scenario.

        An aspirational scenario means the attribute has no
        concrete grounding — it must not count toward the threshold.
        """
        confirmed = [
            a for a in self.attributes
            if a.attribute_id in self.confirmed_attributes
            and a.scenarios
            and a.scenarios[0].completeness != "aspirational"
        ]
        return len(confirmed) >= 3
