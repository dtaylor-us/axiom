"""Pydantic output models for every pipeline stage.

Each class here represents the top-level JSON object that a pipeline tool
expects back from the LLM. These models serve two purposes:

  1. JSON schema derivation — each model's schema is registered in
     app.llm.schemas.SCHEMAS and passed to LLMClient.complete() so the
     provider can enforce the output layout at the API boundary (Layer 1).

  2. Pydantic validation — the parsed dict from each LLM response is
     validated against the model before being written to ArchitectureContext,
     catching structural problems that slipped past Layer 1 (Layer 2).

Schemas are intentionally permissive on inner list-element types so that
OpenAI's strict schema enforcement can accept them. Detailed validation
of inner fields is performed by each tool's own logic after construction.

Do not recompute schemas at call time — import from app.llm.schemas instead.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stage 1 — requirement_parsing
# ---------------------------------------------------------------------------

class ParsedRequirements(BaseModel):
    """Top-level output from RequirementParserTool."""

    domain: str = ""
    system_type: str = ""
    functional_requirements: list[dict] = Field(default_factory=list)
    non_functional_requirements: list[dict] = Field(default_factory=list)
    constraints: list[dict] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    integration_points: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 2 — requirement_challenge
# ---------------------------------------------------------------------------

class MissingRequirement(BaseModel):
    """A missing requirement found by the challenge stage."""

    area: str = ""
    description: str = ""
    impact_if_ignored: str = ""


class RequirementAmbiguity(BaseModel):
    """An ambiguous requirement term found by the challenge stage."""

    term: str = ""
    context: str = ""
    possible_interpretations: list[str] = Field(default_factory=list)


class HiddenAssumption(BaseModel):
    """An unstated assumption found by the challenge stage."""

    assumption: str = ""
    risk_if_wrong: str = ""


class ClarifyingQuestion(BaseModel):
    """A question that blocks architecture decision-making."""

    question: str = ""
    references: str = ""
    blocks_decision: str = ""


class ArchitectureOverrideOutput(BaseModel):
    """Detected architecture style override from the user message."""

    type: Literal["pinned", "candidate_set", "rejection", "none"] = "none"
    styles: list[str] = Field(default_factory=list)
    raw_instruction: str = ""
    detected_confidence: Literal["high", "medium", "low"] = "low"


class BuyVsBuildPreferencesOutput(BaseModel):
    """Detected buy-vs-build preference signals from the user message."""

    prefer_open_source: bool = False
    avoid_vendor_lockin: bool = False
    existing_tools: list[str] = Field(default_factory=list)
    build_preference: Literal["build", "buy", "adopt", "neutral"] = "neutral"
    budget_constrained: bool = False
    raw_signals: list[str] = Field(default_factory=list)


class ChallengeOutput(BaseModel):
    """Top-level output from RequirementChallengeEngineTool."""

    missing_requirements: list[MissingRequirement] = Field(default_factory=list)
    ambiguities: list[RequirementAmbiguity] = Field(default_factory=list)
    hidden_assumptions: list[HiddenAssumption] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    architecture_override: ArchitectureOverrideOutput = Field(
        default_factory=ArchitectureOverrideOutput
    )
    buy_vs_build_preferences: BuyVsBuildPreferencesOutput = Field(
        default_factory=BuyVsBuildPreferencesOutput
    )


# ---------------------------------------------------------------------------
# Stage 3 — scenario_modeling
# ---------------------------------------------------------------------------

class ScenarioOutput(BaseModel):
    """Top-level output from ScenarioModelerTool."""

    scenarios: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 4 — characteristic_inference
# ---------------------------------------------------------------------------

class CharacteristicItem(BaseModel):
    """A single inferred architecture characteristic."""

    name: str = ""
    justification: str = ""
    measurable_target: str = ""
    current_requirement_coverage: str = ""
    tensions_with: list[str] = Field(default_factory=list)


class CharacteristicOutput(BaseModel):
    """Top-level output from CharacteristicReasoningEngine."""

    characteristics: list[CharacteristicItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 4b — tactics_recommendation
# ---------------------------------------------------------------------------

class TacticsOutput(BaseModel):
    """Top-level output from TacticsAdvisorTool."""

    tactics: list[dict] = Field(default_factory=list)
    tactics_summary: str = ""


# ---------------------------------------------------------------------------
# Stage 5 — conflict_analysis
# ---------------------------------------------------------------------------

class ConflictOutput(BaseModel):
    """Top-level output from CharacteristicConflictAnalyzer."""

    conflicts: list[dict] = Field(default_factory=list)
    underrepresented_characteristics: list[str] = Field(default_factory=list)
    overspecified_characteristics: list[str] = Field(default_factory=list)
    tension_summary: str = ""


# ---------------------------------------------------------------------------
# Stage 6 — architecture_generation
# ---------------------------------------------------------------------------

class ArchitectureDesign(BaseModel):
    """Top-level output from ArchitectureGeneratorTool."""

    style: str = ""
    style_selection: dict = Field(default_factory=dict)
    components: list[dict] = Field(default_factory=list)
    interactions: list[dict] = Field(default_factory=list)
    primary_flow: dict = Field(default_factory=dict)
    deployment_view: dict = Field(default_factory=dict)
    when_to_reconsider_this_style: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 6b — buy_vs_build_analysis
# ---------------------------------------------------------------------------

class BuyVsBuildOutput(BaseModel):
    """Top-level output from BuyVsBuildAnalyzerTool."""

    buy_vs_build_analysis: list[dict] = Field(default_factory=list)
    buy_vs_build_summary: str = ""


# ---------------------------------------------------------------------------
# Stage 8 — trade_off_analysis
# ---------------------------------------------------------------------------

class TradeOffOutput(BaseModel):
    """Top-level output from TradeOffEngine."""

    trade_offs: list[dict] = Field(default_factory=list)
    trade_off_dominant_tension: str = ""


# ---------------------------------------------------------------------------
# Stage 9 — adl_generation
# ---------------------------------------------------------------------------

class ADLOutput(BaseModel):
    """Top-level output from ADLGeneratorV2Tool."""

    adl_blocks: list[dict] = Field(default_factory=list)
    adl_document: str = ""


# ---------------------------------------------------------------------------
# Stage 10 — weakness_analysis
# ---------------------------------------------------------------------------

class WeaknessOutput(BaseModel):
    """Top-level output from WeaknessAnalyzerTool."""

    weaknesses: list[dict] = Field(default_factory=list)
    weakness_summary: str = ""


# ---------------------------------------------------------------------------
# Stage 11 — fmea_analysis
# ---------------------------------------------------------------------------

class FMEAOutput(BaseModel):
    """Top-level output from FMEAPlusTool."""

    fmea_risks: list[dict] = Field(default_factory=list)
    fmea_critical_risks: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Item 4 — diagram_generation (single-type call)
# ---------------------------------------------------------------------------

class SingleDiagramOutput(BaseModel):
    """Output from a single-diagram LLM call in DiagramGeneratorTool."""

    type: str = ""
    title: str = ""
    description: str = ""
    mermaid_source: str = ""
    characteristic_addressed: str = ""
