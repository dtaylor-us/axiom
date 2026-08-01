"""Tests for heuristic conflict detection in the classification tool."""

from __future__ import annotations

from app.models.contracts import (
    ClassificationCategory,
    ClassifiedRequirement,
    ClassifiedRequirementSet,
    ConfidenceLevel,
    RequirementType,
)
from app.tools.classification_tool import ClassificationTool


def _requirement(requirement_id: str, statement: str) -> ClassifiedRequirement:
    return ClassifiedRequirement(
        requirement_id=requirement_id,
        category=ClassificationCategory.CONSTRAINTS,
        statement=statement,
        type=RequirementType.CONSTRAINT,
        confidence=ConfidenceLevel.HIGH,
        is_inferred=False,
        inference_reasoning=None,
        source_document_ids=["doc-1"],
        source_excerpts=[statement],
        ambiguities=[],
    )


def _classified_set(requirements: list[ClassifiedRequirement]) -> ClassifiedRequirementSet:
    return ClassifiedRequirementSet(
        session_id="session-1",
        requirements=requirements,
        total_count=len(requirements),
        by_category={"constraints": len(requirements)},
        by_confidence={"HIGH": len(requirements)},
        conflicts=[],
    )


def test_detect_obvious_conflicts_finds_cosmosdb_vs_postgresql(llm_client):
    """Heuristic should record mutual-exclusion conflicts for datastore choices."""
    classified = _classified_set(
        [
            _requirement("REQ-1", "The platform must use Azure Cosmos DB."),
            _requirement("REQ-2", "The platform must use PostgreSQL for storage."),
        ]
    )

    result = ClassificationTool(llm_client)._detect_obvious_conflicts(classified)

    assert len(result.conflicts) == 1


def test_detect_obvious_conflicts_finds_aws_vs_azure(llm_client):
    """Heuristic should catch cloud-provider contradictions."""
    classified = _classified_set(
        [
            _requirement("REQ-1", "The service must run only on AWS."),
            _requirement("REQ-2", "The service must be deployed on Azure."),
        ]
    )

    result = ClassificationTool(llm_client)._detect_obvious_conflicts(classified)

    assert len(result.conflicts) == 1


def test_detect_obvious_conflicts_does_not_flag_same_family_technologies(llm_client):
    """Matching technology family statements should not be flagged as contradictory."""
    classified = _classified_set(
        [
            _requirement("REQ-1", "Use PostgreSQL for transactional workloads."),
            _requirement("REQ-2", "Postgres backups must run every 15 minutes."),
        ]
    )

    result = ClassificationTool(llm_client)._detect_obvious_conflicts(classified)

    assert result.conflicts == []


def test_detect_obvious_conflicts_does_not_duplicate_existing_conflicts(llm_client):
    """Heuristic should not append duplicates when conflict is already recorded."""
    requirements = [
        _requirement("REQ-1", "Use Azure Cosmos DB for persistence."),
        _requirement("REQ-2", "Use PostgreSQL as the primary database."),
    ]
    existing_conflict = {
        "requirement_ids": ["REQ-1", "REQ-2"],
        "description": "Existing conflict.",
        "interpretations": [],
        "clarification_question": "Which database is authoritative?",
    }
    classified = _classified_set(requirements).model_copy(
        update={"conflicts": [existing_conflict]}
    )

    result = ClassificationTool(llm_client)._detect_obvious_conflicts(classified)

    assert len(result.conflicts) == 1
