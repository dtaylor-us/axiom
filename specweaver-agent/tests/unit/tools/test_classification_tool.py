"""Tests for the classification tool."""

from __future__ import annotations

import json

import pytest

from app.models.contracts import (
    ClassificationCategory,
    ClassifiedRequirement,
    ClassifiedRequirementSet,
)
from app.tools.classification_tool import ClassificationTool
from tests.conftest import classified_json


@pytest.mark.asyncio
async def test_run_calls_llm_with_all_extraction_results(
    context,
    llm_client,
    extraction_result,
    classified_set,
):
    context.extraction_results = [extraction_result]
    llm_client.complete.return_value = classified_json(classified_set)
    await ClassificationTool(llm_client).run(context)
    assert llm_client.complete.call_count == 1
    assert "extraction_results" not in llm_client.complete.call_args.args[0]


@pytest.mark.asyncio
async def test_run_produces_classified_requirement_set(
    context,
    llm_client,
    extraction_result,
    classified_set,
):
    context.extraction_results = [extraction_result]
    llm_client.complete.return_value = classified_json(classified_set)
    result = await ClassificationTool(llm_client).run(context)
    assert result.classified_requirements == classified_set


@pytest.mark.asyncio
async def test_run_merges_duplicate_requirements_from_two_documents(
    context,
    llm_client,
    extraction_result,
    classified_requirement,
):
    context.extraction_results = [extraction_result, extraction_result]
    merged = classified_requirement.model_copy(
        update={
            "source_document_ids": ["doc-1", "doc-2"],
            "source_excerpts": ["SSO is required", "Single sign-on is required"],
        }
    )
    llm_client.complete.return_value = classified_json(
        ClassifiedRequirementSet(
            session_id="session-1",
            requirements=[merged],
            total_count=1,
            by_category={"functional": 1},
            by_confidence={"HIGH": 1},
        )
    )
    result = await ClassificationTool(llm_client).run(context)
    assert len(result.classified_requirements.requirements) == 1


@pytest.mark.asyncio
async def test_run_preserves_all_source_document_ids_after_merge(
    context,
    llm_client,
    extraction_result,
    classified_requirement,
):
    context.extraction_results = [extraction_result]
    merged = classified_requirement.model_copy(
        update={"source_document_ids": ["doc-1", "doc-2"]}
    )
    llm_client.complete.return_value = classified_json(
        ClassifiedRequirementSet(
            session_id="session-1",
            requirements=[merged],
            total_count=1,
            by_category={"functional": 1},
            by_confidence={"HIGH": 1},
        )
    )
    result = await ClassificationTool(llm_client).run(context)
    assert result.classified_requirements.requirements[0].source_document_ids == [
        "doc-1",
        "doc-2",
    ]


@pytest.mark.asyncio
async def test_run_preserves_all_ambiguities_after_merge(
    context,
    llm_client,
    extraction_result,
    classified_requirement,
):
    context.extraction_results = [extraction_result]
    merged = classified_requirement.model_copy(update={"ambiguities": ["A", "B"]})
    llm_client.complete.return_value = classified_json(
        ClassifiedRequirementSet(
            session_id="session-1",
            requirements=[merged],
            total_count=1,
            by_category={"functional": 1},
            by_confidence={"HIGH": 1},
        )
    )
    result = await ClassificationTool(llm_client).run(context)
    assert result.classified_requirements.requirements[0].ambiguities == ["A", "B"]


@pytest.mark.asyncio
async def test_run_does_not_merge_requirements_with_different_constraints(
    context,
    llm_client,
    extraction_result,
    classified_requirement,
):
    context.extraction_results = [extraction_result]
    req2 = ClassifiedRequirement(
        **{
            **classified_requirement.model_dump(),
            "requirement_id": "REQ-2",
            "statement": "The system shall respond within 200ms.",
            "category": ClassificationCategory.NON_FUNCTIONAL,
        }
    )
    llm_client.complete.return_value = classified_json(
        ClassifiedRequirementSet(
            session_id="session-1",
            requirements=[classified_requirement, req2],
            total_count=2,
            by_category={"functional": 1, "non_functional": 1},
            by_confidence={"HIGH": 2},
        )
    )
    result = await ClassificationTool(llm_client).run(context)
    assert len(result.classified_requirements.requirements) == 2


@pytest.mark.asyncio
async def test_run_adds_classification_to_completed_stages(
    context,
    llm_client,
    extraction_result,
    classified_set,
):
    context.extraction_results = [extraction_result]
    llm_client.complete.return_value = classified_json(classified_set)
    result = await ClassificationTool(llm_client).run(context)
    assert "classification" in result.completed_stages


@pytest.mark.asyncio
async def test_run_logs_error_and_falls_back_when_result_is_empty(
    caplog,
    context,
    llm_client,
    extraction_result,
):
    context.extraction_results = [extraction_result]
    empty = ClassifiedRequirementSet(
        session_id="session-1",
        requirements=[],
        total_count=0,
        by_category={},
        by_confidence={},
    )
    llm_client.complete.return_value = classified_json(empty)
    result = await ClassificationTool(llm_client).run(context)
    assert "empty output despite extracted requirements" in caplog.text
    assert len(result.classified_requirements.requirements) == 1


@pytest.mark.asyncio
async def test_run_repairs_missing_category_from_requirement_type(
    context,
    llm_client,
    extraction_result,
):
    context.extraction_results = [extraction_result]
    llm_client.complete.return_value = json.dumps(
        {
            "session_id": "session-1",
            "requirements": [
                {
                    "requirement_id": "REQ-1",
                    "statement": "The system shall support SSO.",
                    "type": "FUNCTIONAL",
                    "confidence": "HIGH",
                    "is_inferred": False,
                    "inference_reasoning": None,
                    "source_document_ids": ["doc-1"],
                    "source_excerpts": ["SSO is required."],
                    "ambiguities": [],
                }
            ],
            "total_count": 1,
            "by_category": {},
            "by_confidence": {},
            "conflicts": [],
        }
    )

    result = await ClassificationTool(llm_client).run(context)

    assert result.classified_requirements.requirements[0].category == ClassificationCategory.FUNCTIONAL
    assert result.classified_requirements.by_category == {"functional": 1}


@pytest.mark.asyncio
async def test_run_normalizes_lowercase_requirement_types(
    context,
    llm_client,
    extraction_result,
):
    """Lowercase OpenAI enum values should be normalized before validation."""
    context.extraction_results = [extraction_result]
    llm_client.complete.return_value = json.dumps(
        {
            "session_id": "session-1",
            "requirements": [
                {
                    "requirement_id": "REQ-1",
                    "statement": "The system shall support SSO.",
                    "type": "functional",
                    "confidence": "HIGH",
                    "is_inferred": False,
                    "inference_reasoning": None,
                    "source_document_ids": ["doc-1"],
                    "source_excerpts": ["SSO is required."],
                    "ambiguities": [],
                }
            ],
            "total_count": 1,
            "by_category": {},
            "by_confidence": {},
            "conflicts": [],
        }
    )

    result = await ClassificationTool(llm_client).run(context)

    assert result.classified_requirements.requirements[0].type == "FUNCTIONAL"
    assert result.classified_requirements.requirements[0].category == ClassificationCategory.FUNCTIONAL


@pytest.mark.asyncio
async def test_run_repairs_missing_inference_reasoning_for_inferred_requirement(
    context,
    llm_client,
    extraction_result,
):
    """Inferred requirements must have reasoning even when omitted by LLM output."""
    context.extraction_results = [extraction_result]
    llm_client.complete.return_value = json.dumps(
        {
            "session_id": "session-1",
            "requirements": [
                {
                    "requirement_id": "REQ-1",
                    "category": "functional",
                    "statement": "The system shall support SSO.",
                    "type": "FUNCTIONAL",
                    "confidence": "INFERRED",
                    "is_inferred": True,
                    "inference_reasoning": None,
                    "source_document_ids": ["doc-1"],
                    "source_excerpts": ["Enterprise customers use SSO."],
                    "ambiguities": [],
                }
            ],
            "total_count": 1,
            "by_category": {},
            "by_confidence": {},
            "conflicts": [],
        }
    )

    result = await ClassificationTool(llm_client).run(context)

    assert result.classified_requirements.requirements[0].inference_reasoning is not None
