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

import hashlib
import logging
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

logger = logging.getLogger(__name__)

BUSINESS_OUTCOME_SIGNALS = {
    "rate",
    "satisfaction",
    "experience",
    "quality",
    "efficiency",
    "reduction",
    "improvement",
    "better",
    "worse",
    "more",
    "less",
}

OPERATIONAL_METRIC_SIGNALS = {
    "ms",
    "milliseconds",
    "seconds",
    "minutes",
    "%",
    "percent",
    "per second",
    "per minute",
    "requests/second",
    "requests per second",
    "transactions/second",
    "transactions per second",
    "rps",
    "tps",
    "requests",
    "transactions",
    "availability",
    "uptime",
    "recovery",
    "latency",
    "throughput",
    "sla",
}

ScenarioCompleteness = Literal[
    "complete",
    "partial",
    "needs_measure",
    "needs_operational_metric",
    "aspirational",
]

COMPLETENESS_ORDER = {
    "complete": 0,
    "needs_operational_metric": 1,
    "needs_measure": 2,
    "partial": 3,
    "aspirational": 4,
}


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
        if not contains_operational_metric(meas):
            return "needs_operational_metric"
        return "complete"
    if has_response and has_stimulus and not has_measure:
        return "needs_measure"
    if populated >= 2:
        return "partial"
    return "aspirational"


def contains_operational_metric(response_measure: str) -> bool:
    """
    Return True when a response measure contains an operational target.

    Args:
        response_measure: Candidate response measure text.

    Returns:
        True for latency, throughput, SLA, recovery, or availability
        targets that can be verified by tests, dashboards, or reports.
    """
    measure = response_measure.lower()
    return any(sig in measure for sig in OPERATIONAL_METRIC_SIGNALS)


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

    def is_operational_metric(self) -> bool:
        """
        Return True when response_measure is an operational metric.

        Returns:
            True when the response measure has a verifiable operational
            threshold such as latency, throughput, SLA, recovery, or uptime.
        """
        return contains_operational_metric(self.response_measure)

    def model_post_init(self, __context: Any) -> None:
        """Recompute completeness so empty scenarios cannot be marked complete."""
        self.completeness = self.compute_completeness()


class ResolvedAnswer(BaseModel):
    """
    Traceable resolution of one open question against workshop evidence.

    Stored on ``ElicitedAttribute`` so the UI and API can show what was
    inferred from which user language.
    """
    question: str
    answer: str
    resolved_in_turn: int
    evidence_quote: str = ""


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

    def is_operational_metric(self) -> bool:
        """
        Return True when response_measure is an operational metric.

        Returns:
            True when the response measure has a verifiable operational
            threshold such as latency, throughput, SLA, recovery, or uptime.
        """
        return contains_operational_metric(self.response_measure)


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
    resolved_answers: list[ResolvedAnswer] = Field(default_factory=list)
    # Structured answers to previously open questions (traceability)
    questions_resolved_count: int = 0
    # Running total of resolutions applied — monotonic across the session
    last_update_summary: str = ""
    # Plain-English description of the most recent change to this attribute
    last_updated_turn: int = 0
    # Conversation turn that last modified resolution fields
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
    gap_question_type: Literal[
        "mechanism",    # How does X work? What strategies/patterns are used?
        "metric",       # What is the target? How much? How fast?
        "constraint",   # What are the limits? What is not allowed?
        "stakeholder",  # Who cares? Who decides?
        "timeline",     # When? How often? What is the deadline?
        "unknown",
    ] = "unknown"

    architectural_impact: Literal[
        "blocks_attribute_confirmation",
        "blocks_scenario_completion",
        "reduces_confidence",
        "informational",
    ] = "informational"
    confidence_impact: float = 0.0

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

    @property
    def effective_resolution_threshold(self) -> float:
        """
        Returns the resolution threshold adjusted for question type.

        Mechanism questions resolve at a lower threshold because describing
        multiple mechanisms is sufficient evidence even without a specific
        measurable target. Metric questions require a higher bar — a vague
        statement is not the same as a number.
        """
        base = (
            0.9 if self.priority == "critical" else
            0.75 if self.priority == "high" else
            0.6
        )
        if self.gap_question_type == "mechanism":
            return base - 0.10
        if self.gap_question_type == "metric":
            return base + 0.10
        return base

    @computed_field
    @property
    def filled(self) -> bool:
        """True when ``resolution_confidence`` meets the effective threshold."""
        return self.resolution_confidence >= self.effective_resolution_threshold

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


class UtilityTreeNode(BaseModel):
    """
    A node in the SEI QAW utility tree.

    The utility tree organises scenarios by:
      - Quality attribute (top level)
      - Attribute refinement (mid level — specific concern within the attribute)
      - Scenario with importance/risk scores (leaf)

    Scenarios scored (H,H) are architectural drivers — the decisions that
    most constrain the architecture. Reference: Bass, Clements, Kazman
    "Software Architecture in Practice" 4th ed. ch. 2.
    """
    node_id:             str
    attribute_name:      str
    refinement:          str
    # The specific sub-concern within the attribute.
    # Example: "Availability during peak fulfillment windows"
    scenario_id:         str
    scenario_title:      str
    business_importance: Literal["H", "M", "L"]
    # H: failure here damages the business significantly
    # M: failure here is painful but manageable
    # L: failure here is acceptable in the short term
    technical_risk:      Literal["H", "M", "L"]
    # H: achieving this is architecturally challenging
    # M: requires care but standard patterns apply
    # L: straightforward to achieve
    priority_label:      str
    # e.g. "(H,H) — Architectural driver"
    rationale:           str
    # Why this business importance and technical risk score


class UtilityTree(BaseModel):
    """
    The complete utility tree for a workshop session.

    Generated when has_sufficient_for_utility_tree is True (5+ scenarios
    across 3+ attributes). Updated on every subsequent turn — the latest
    tree is always authoritative.
    """
    generated_at_turn:     int
    total_scenarios:       int
    architectural_drivers: list[str] = Field(default_factory=list)
    # scenario_ids with (H,H) or (H,M) scores
    nodes:                 list[UtilityTreeNode] = Field(default_factory=list)
    generation_rationale:  str = ""
    # One paragraph explaining the prioritisation approach


class ArchitectureImplication(BaseModel):
    """
    An architectural requirement derived from a specific scenario.

    Implications are not architecture decisions. They state what must be
    true about the system so the architecture pipeline can choose suitable
    mechanisms later.

    Each implication is traceable to the specific scenario that necessitates
    it. The format enforced by the prompt is:
    "Because [scenario stimulus and environment], [quality property] must be
    [measurable or describable condition]."
    """
    implication_id:       str
    # e.g. IMP-001
    source_scenario_id:   str
    source_scenario_title: str
    implication:          str
    # Requirement in plain language, never a mechanism prescription.
    tradeoff:             str = ""
    # Which quality attribute is deprioritised to satisfy the requirement.
    affected_quality_attrs: list[str] = Field(default_factory=list)
    # Quality attributes exercised by this requirement.
    constraint_type: Literal[
        "safety",
        "consistency",
        "availability",
        "performance",
        "security",
        "recoverability",
        "observability",
        "operational",
    ]
    constraint_classification: Literal[
        "functional_constraint",
        "operational_constraint",
        "quality_constraint",
        "compliance_constraint",
        "business_constraint",
        "inferred_assumption",
    ] = "functional_constraint"
    strength: Literal["must", "should", "may"]
    # must:   the architecture cannot work without this
    # should: strongly recommended given the scenario
    # may:    worth considering given the scenario
    measurable_condition: str = ""
    # Testable condition from the scenario response measure where available.


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

    # SEI QAW utility tree — generated when has_sufficient_for_utility_tree is True.
    # Updated on every subsequent turn; the latest tree is always authoritative.
    utility_tree: UtilityTree | None = None

    # Architectural implications derived from driver scenarios.
    # Populated after the utility tree is generated.
    architecture_implications: list[ArchitectureImplication] = Field(
        default_factory=list
    )

    @property
    def deduplicated_scenarios(self) -> list[WorkshopScenario]:
        """
        Return scenarios with semantic duplicates removed.

        Uses a content hash of stimulus, artifact, and response. When
        duplicates exist, the more complete scenario is kept and evidence
        from the duplicate is merged into the keeper.

        Returns:
            Scenario list with one canonical scenario per operational concern.
        """
        seen: dict[str, WorkshopScenario] = {}

        for scenario in self.scenarios:
            content = (
                scenario.stimulus.lower().strip()
                + scenario.artifact.lower().strip()
                + scenario.response.lower().strip()
            )
            key = hashlib.md5(content.encode()).hexdigest()[:12]

            if key not in seen:
                seen[key] = scenario
                continue

            existing = seen[key]
            scenario_rank = COMPLETENESS_ORDER.get(scenario.completeness, 4)
            existing_rank = COMPLETENESS_ORDER.get(existing.completeness, 4)
            keeper = scenario if scenario_rank < existing_rank else existing
            duplicate = existing if keeper is scenario else scenario
            merged_attributes = list(dict.fromkeys(
                keeper.exercises_attributes + duplicate.exercises_attributes
            ))
            seen[key] = keeper.model_copy(update={
                "exercises_attributes": merged_attributes,
                "evidence_quote": (
                    keeper.evidence_quote or duplicate.evidence_quote
                ),
            })

        result = list(seen.values())
        if len(result) < len(self.scenarios):
            logger.info(
                "Scenario deduplication: %d -> %d. session=%s",
                len(self.scenarios),
                len(result),
                self.session_id,
            )
        return result

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
            "needs_operational_metric": 0,
            "needs_measure": 0,
            "partial": 0,
            "aspirational": 0,
        }
        for s in self.deduplicated_scenarios:
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

    @property
    def has_sufficient_for_utility_tree(self) -> bool:
        """
        Returns True when the session has enough scenarios and attributes
        to generate a meaningful utility tree.

        Threshold: at least 5 scenarios with at least partial completeness,
        across at least 3 distinct attributes.
        """
        partial_or_better = [
            s for s in self.deduplicated_scenarios
            if s.completeness in (
                "complete",
                "partial",
                "needs_measure",
                "needs_operational_metric",
            )
        ]
        covered_attributes = {
            attr
            for s in partial_or_better
            for attr in s.exercises_attributes
        }
        return (
            len(partial_or_better) >= 5
            and len(covered_attributes) >= 3
        )
