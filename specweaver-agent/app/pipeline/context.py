"""Typed state object for the SpecWeaver extraction pipeline."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.contracts import (
    ArchInputPackage,
    ClassifiedRequirementSet,
    ConflictDetectionResult,
    ConsolidationResult,
    DocumentPayload,
    ExtractionResult,
    GapAnalysisResult,
)


class SpecWeaverContext(BaseModel):
    """
    Shared state for the SpecWeaver extraction pipeline.

    Each stage reads from this context and writes its output back to it. No
    stage communicates through global state or side channels.
    """

    session_id: str
    documents: list[DocumentPayload] = Field(default_factory=list)
    project_memory_context: dict[str, Any] | None = None
    extraction_results: list[ExtractionResult] = Field(default_factory=list)
    classified_requirements: Optional[ClassifiedRequirementSet] = None
    consolidation_result: Optional[ConsolidationResult] = None
    gap_analysis_result: Optional[GapAnalysisResult] = None
    conflict_detection_result: Optional[ConflictDetectionResult] = None
    arch_input_package: Optional[ArchInputPackage] = None
    pipeline_errors: list[str] = Field(default_factory=list)
    completed_stages: list[str] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
