"""Data contracts shared between specweaver-api and specweaver-agent."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_camel(name: str) -> str:
    """Convert a snake_case field name to lower camelCase for Java DTOs."""
    parts = name.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class ApiModel(BaseModel):
    """Base model that accepts snake_case and emits Java-style camelCase."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        use_enum_values=True,
    )


class DocumentType(str, Enum):
    """Supported document types received from specweaver-api."""

    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    EMAIL = "email"


class ConfidenceLevel(str, Enum):
    """Confidence labels assigned during requirement extraction."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFERRED = "INFERRED"


class RequirementType(str, Enum):
    """Requirement types extracted from source documents."""

    FUNCTIONAL = "FUNCTIONAL"
    NON_FUNCTIONAL = "NON_FUNCTIONAL"
    CONSTRAINT = "CONSTRAINT"
    ASSUMPTION = "ASSUMPTION"
    BUSINESS_RULE = "BUSINESS_RULE"
    INTEGRATION = "INTEGRATION"
    DATA = "DATA"
    OPERATIONAL = "OPERATIONAL"


class ClassificationCategory(str, Enum):
    """Top-level categories used in the classified requirement set."""

    BUSINESS_OBJECTIVES = "business_objectives"
    SYSTEM_SCOPE = "system_scope"
    ACTORS_AND_USERS = "actors_and_users"
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINTS = "constraints"
    INTEGRATIONS = "integrations"
    DATA_CONSIDERATIONS = "data_considerations"
    ASSUMPTIONS = "assumptions"
    RISKS = "risks"


class DocumentPayload(ApiModel):
    """Pre-extracted document text sent by specweaver-api."""

    document_id: str
    document_type: DocumentType
    content: str
    filename: Optional[str] = None
    source_label: Optional[str] = None

    @field_validator("document_type", mode="before")
    @classmethod
    def normalize_document_type(cls, value: Any) -> Any:
        """
        Accept Java enum names while storing the canonical Python values.

        Args:
            value: Incoming document type.

        Returns:
            Normalized document type value.
        """
        if isinstance(value, str):
            return value.lower()
        return value


class ExtractionRequest(ApiModel):
    """Request body for POST /agent/extract."""

    session_id: str
    documents: list[DocumentPayload]


class ExtractedRequirement(ApiModel):
    """Single requirement extracted from one source document."""

    requirement_id: str
    type: RequirementType
    statement: str
    confidence: ConfidenceLevel
    is_inferred: bool
    inference_reasoning: Optional[str] = Field(
        default=None,
        description="Required when is_inferred=True.",
    )
    source_document_id: str
    source_excerpt: str = Field(description="Verbatim excerpt - never empty.")
    ambiguities: list[str] = Field(default_factory=list)


class ExtractionResult(ApiModel):
    """Extraction result for a single source document."""

    session_id: str
    document_id: str
    extracted_requirements: list[ExtractedRequirement]
    extraction_notes: list[str] = Field(default_factory=list)


class ClassifiedRequirement(ApiModel):
    """Requirement after cross-document classification and duplicate merging."""

    requirement_id: str
    category: ClassificationCategory
    statement: str
    type: RequirementType
    confidence: ConfidenceLevel
    is_inferred: bool
    inference_reasoning: Optional[str] = None
    source_document_ids: list[str]
    source_excerpts: list[str]
    ambiguities: list[str]


class ClassifiedRequirementSet(ApiModel):
    """Unified classified requirements for a SpecWeaver session."""

    session_id: str
    requirements: list[ClassifiedRequirement]
    total_count: int
    by_category: dict[str, int]
    by_confidence: dict[str, int]
    conflicts: list[dict] = Field(default_factory=list)


class ConsolidationGroup(ApiModel):
    """Semantically similar requirements identified before classification."""

    group_id: str
    requirements: list[ExtractedRequirement]
    similarity_score: float = Field(
        description=(
            "Cosine similarity of the group centroid. 0.0-1.0. "
            "Higher = more similar."
        )
    )
    is_duplicate_group: bool = Field(
        description=(
            "True when requirements are semantic duplicates and should be "
            "merged. False when they are related but distinct."
        )
    )


class ConsolidationResult(ApiModel):
    """Result of vector-based semantic requirement consolidation."""

    session_id: str
    consolidated_groups: list[ConsolidationGroup]
    merged_requirements: list[ExtractedRequirement] = Field(
        description=(
            "Deduplicated requirements after merging duplicate groups. "
            "This replaces the raw extraction_results for downstream stages."
        )
    )
    duplicate_count: int = Field(
        description="Number of requirements removed by merging."
    )
    original_count: int
    consolidated_count: int


class GapSeverity(str, Enum):
    """Severity labels for missing requirement areas."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GapArea(ApiModel):
    """Missing requirement area found during Phase 1b gap analysis."""

    gap_id: str
    area: str = Field(
        description=(
            "Short label for the missing area. e.g. 'Performance requirements' "
            "or 'Data retention policy'"
        )
    )
    severity: GapSeverity
    explanation: str = Field(
        description="Why this gap matters for architecture decision-making."
    )
    clarification_question: str = Field(
        description=(
            "The specific question a stakeholder must answer to fill this gap."
        )
    )
    affected_categories: list[str] = Field(
        description="Which classification categories this gap affects."
    )


class GapAnalysisResult(ApiModel):
    """Structured output from the Phase 1b gap analysis agent."""

    session_id: str
    gaps: list[GapArea]
    gap_count: int
    by_severity: dict[str, int]


class ConflictItem(ApiModel):
    """Structured contradiction between two or more requirements."""

    conflict_id: str
    requirement_ids: list[str]
    description: str
    interpretations: list[str] = Field(
        description=(
            "Two or more plausible interpretations of how the conflict might "
            "be resolved. Never resolve - only interpret."
        )
    )
    clarification_question: str


class ConflictDetectionResult(ApiModel):
    """Structured output from the Phase 1b conflict detection agent."""

    session_id: str
    conflicts: list[ConflictItem]
    conflict_count: int


class ArchInputPackage(ApiModel):
    """Final package sent back to specweaver-api for Archon handoff."""

    package_id: str
    session_id: str
    created_at: str
    readiness_score: float = 0.0
    system_description: str
    requirements: list[ClassifiedRequirement]
    gaps: list[GapArea] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    source_documents: list[dict]
    total_requirements: int
    high_confidence_count: int
    inferred_count: int
    duplicate_count: int = Field(
        default=0,
        description="Requirements removed by consolidation.",
    )
    gap_count: int = Field(default=0)
    conflict_count: int = Field(default=0)


class ExtractionResponse(ApiModel):
    """Response body returned to specweaver-api after extraction."""

    session_id: str
    arch_input_package_json: str
    success: bool
    error_message: Optional[str] = None
