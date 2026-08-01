"""Shared test fixtures for specweaver-agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.models.contracts import (
    ClassificationCategory,
    ClassifiedRequirement,
    ClassifiedRequirementSet,
    ConfidenceLevel,
    DocumentPayload,
    DocumentType,
    ExtractedRequirement,
    ExtractionResult,
    RequirementType,
)
from app.pipeline.context import SpecWeaverContext


@pytest.fixture
def document() -> DocumentPayload:
    """Return a representative input document."""
    return DocumentPayload(
        document_id="doc-12345678",
        document_type=DocumentType.PLAIN_TEXT,
        content="The system shall support SSO. Response time must be under 200ms.",
        filename="requirements.txt",
        source_label="Product brief",
    )


@pytest.fixture
def extracted_requirement() -> ExtractedRequirement:
    """Return a representative extracted requirement."""
    return ExtractedRequirement(
        requirement_id="REQ-doc-1234-001",
        type=RequirementType.FUNCTIONAL,
        statement="The system shall support SSO.",
        confidence=ConfidenceLevel.HIGH,
        is_inferred=False,
        source_document_id="doc-12345678",
        source_excerpt="The system shall support SSO.",
        ambiguities=[],
    )


@pytest.fixture
def extraction_result(extracted_requirement: ExtractedRequirement) -> ExtractionResult:
    """Return a representative extraction result."""
    return ExtractionResult(
        session_id="session-1",
        document_id="doc-12345678",
        extracted_requirements=[extracted_requirement],
        extraction_notes=[],
    )


@pytest.fixture
def classified_requirement() -> ClassifiedRequirement:
    """Return a representative classified requirement."""
    return ClassifiedRequirement(
        requirement_id="REQ-doc-1234-001",
        category=ClassificationCategory.FUNCTIONAL,
        statement="The system shall support SSO.",
        type=RequirementType.FUNCTIONAL,
        confidence=ConfidenceLevel.HIGH,
        is_inferred=False,
        source_document_ids=["doc-12345678"],
        source_excerpts=["The system shall support SSO."],
        ambiguities=[],
    )


@pytest.fixture
def classified_set(classified_requirement: ClassifiedRequirement) -> ClassifiedRequirementSet:
    """Return a representative classified requirement set."""
    return ClassifiedRequirementSet(
        session_id="session-1",
        requirements=[classified_requirement],
        total_count=1,
        by_category={"functional": 1},
        by_confidence={"HIGH": 1},
    )


@pytest.fixture
def context(document: DocumentPayload) -> SpecWeaverContext:
    """Return a base pipeline context."""
    return SpecWeaverContext(session_id="session-1", documents=[document])


@pytest.fixture
def llm_client() -> AsyncMock:
    """Return a mocked LLM client."""
    client = AsyncMock()
    client.complete = AsyncMock()
    return client


def extraction_json(result: ExtractionResult) -> str:
    """Serialize an extraction result."""
    return result.model_dump_json()


def classified_json(result: ClassifiedRequirementSet) -> str:
    """Serialize a classified result."""
    return result.model_dump_json()


def formatter_json(description: str = "A system that supports SSO.") -> str:
    """Serialize output formatter LLM response."""
    return json.dumps({"system_description": description})
