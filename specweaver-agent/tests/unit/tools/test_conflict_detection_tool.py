"""Tests for the Phase 1b conflict detection tool."""

from __future__ import annotations

import pytest

from app.llm.client import LLMCallException
from app.models.contracts import (
    ClassificationCategory,
    ClassifiedRequirement,
    ClassifiedRequirementSet,
    ConfidenceLevel,
    ConflictItem,
    RequirementType,
)
from app.tools.conflict_detection_tool import ConflictDetectionTool


def _requirement(requirement_id: str, statement: str) -> ClassifiedRequirement:
    """Build a representative classified requirement."""
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


def _classified(requirements) -> ClassifiedRequirementSet:
    """Build a classified set from supplied requirements."""
    return ClassifiedRequirementSet(
        session_id="session-1",
        requirements=requirements,
        total_count=len(requirements),
        by_category={},
        by_confidence={},
        conflicts=[],
    )


def _conflict(conflict_id: str, requirement_ids: list[str]) -> ConflictItem:
    """Build a representative conflict."""
    return ConflictItem(
        conflict_id=conflict_id,
        requirement_ids=requirement_ids,
        description="Conflicting requirements.",
        interpretations=["Interpretation A.", "Interpretation B."],
        clarification_question="Which interpretation is correct?",
    )


def test_run_heuristics_detects_cosmosdb_vs_postgresql(llm_client):
    """Heuristics should detect mutually exclusive database choices."""
    classified = _classified(
        [
            _requirement("REQ-1", "Use Azure Cosmos DB."),
            _requirement("REQ-2", "Use PostgreSQL."),
        ]
    )

    conflicts = ConflictDetectionTool(llm_client)._run_heuristics(classified)

    assert len(conflicts) == 1
    assert set(conflicts[0].requirement_ids) == {"REQ-1", "REQ-2"}


def test_run_heuristics_detects_cloud_agnostic_vs_azure(llm_client):
    """Heuristics should detect cloud-agnostic versus Azure-only positions."""
    classified = _classified(
        [
            _requirement("REQ-1", "The system must be cloud-agnostic."),
            _requirement("REQ-2", "The system must be deployed on Azure."),
        ]
    )

    conflicts = ConflictDetectionTool(llm_client)._run_heuristics(classified)

    assert len(conflicts) == 1


def test_run_heuristics_returns_empty_when_no_conflicts(llm_client):
    """Unrelated requirements should not produce conflicts."""
    classified = _classified(
        [
            _requirement("REQ-1", "Use PostgreSQL."),
            _requirement("REQ-2", "Backups must run nightly."),
        ]
    )

    conflicts = ConflictDetectionTool(llm_client)._run_heuristics(classified)

    assert conflicts == []


def test_merge_conflicts_deduplicates_overlapping_requirement_ids(llm_client):
    """LLM conflicts with significant overlap should be skipped."""
    existing = _conflict("C-1", ["REQ-1", "REQ-2"])
    duplicate = _conflict("C-2", ["REQ-1", "REQ-2", "REQ-3"])

    result = ConflictDetectionTool(llm_client)._merge_conflicts(
        [existing],
        [duplicate],
    )

    assert result == [existing]


def test_merge_conflicts_preserves_non_overlapping_llm_conflicts(llm_client):
    """Distinct LLM conflicts should be appended."""
    existing = _conflict("C-1", ["REQ-1", "REQ-2"])
    llm_conflict = _conflict("C-2", ["REQ-3", "REQ-4"])

    result = ConflictDetectionTool(llm_client)._merge_conflicts(
        [existing],
        [llm_conflict],
    )

    assert result == [existing, llm_conflict]


@pytest.mark.asyncio
async def test_run_appends_conflict_detection_to_completed_stages(
    context,
    llm_client,
):
    """A successful run should append the conflict_detection stage name."""
    context.classified_requirements = _classified(
        [_requirement("REQ-1", "Use PostgreSQL.")]
    )
    llm_client.complete.return_value = '{"conflicts":[]}'

    result = await ConflictDetectionTool(llm_client).run(context)

    assert "conflict_detection" in result.completed_stages


@pytest.mark.asyncio
async def test_run_sets_conflict_count_correctly(context, llm_client):
    """Conflict count should match merged heuristic plus LLM results."""
    context.classified_requirements = _classified(
        [
            _requirement("REQ-1", "Use Azure Cosmos DB."),
            _requirement("REQ-2", "Use PostgreSQL."),
        ]
    )
    llm_client.complete.return_value = '{"conflicts":[]}'

    result = await ConflictDetectionTool(llm_client).run(context)

    assert result.conflict_detection_result.conflict_count == 1


@pytest.mark.asyncio
async def test_run_continues_with_heuristic_results_when_llm_fails(
    context,
    llm_client,
):
    """LLM failure should not discard deterministic conflict findings."""
    context.classified_requirements = _classified(
        [
            _requirement("REQ-1", "Use Azure Cosmos DB."),
            _requirement("REQ-2", "Use PostgreSQL."),
        ]
    )
    llm_client.complete.side_effect = LLMCallException("provider failed")

    result = await ConflictDetectionTool(llm_client).run(context)

    assert result.conflict_detection_result.conflict_count == 1
