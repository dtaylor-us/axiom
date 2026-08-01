"""Tests for extraction validation and retry repair behavior."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.models.contracts import ConfidenceLevel
from app.tools.extraction_tool import ExtractionTool


@pytest.mark.asyncio
async def test_validate_and_repair_synthesises_inference_reasoning_when_missing(
    llm_client,
    extraction_result,
):
    """Inferred requirements must never keep null reasoning after repair."""
    tool = ExtractionTool(llm_client)
    req = extraction_result.extracted_requirements[0].model_copy(
        update={
            "confidence": ConfidenceLevel.INFERRED,
            "is_inferred": True,
            "inference_reasoning": None,
        }
    )

    repaired = tool._validate_and_repair(
        extraction_result.model_copy(update={"extracted_requirements": [req]})
    )

    assert repaired.extracted_requirements[0].inference_reasoning is not None


@pytest.mark.asyncio
async def test_validate_and_repair_preserves_existing_inference_reasoning(
    llm_client,
    extraction_result,
):
    """Existing reasoning should not be overwritten by repair logic."""
    tool = ExtractionTool(llm_client)
    req = extraction_result.extracted_requirements[0].model_copy(
        update={
            "confidence": ConfidenceLevel.INFERRED,
            "is_inferred": True,
            "inference_reasoning": "Explicitly provided reasoning.",
        }
    )

    repaired = tool._validate_and_repair(
        extraction_result.model_copy(update={"extracted_requirements": [req]})
    )

    assert (
        repaired.extracted_requirements[0].inference_reasoning
        == "Explicitly provided reasoning."
    )


@pytest.mark.asyncio
async def test_validate_and_repair_logs_warning_for_empty_source_excerpt(
    caplog,
    llm_client,
    extraction_result,
):
    """Traceability warning must be emitted when excerpt evidence is missing."""
    tool = ExtractionTool(llm_client)
    req = extraction_result.extracted_requirements[0].model_copy(update={"source_excerpt": ""})

    tool._validate_and_repair(
        extraction_result.model_copy(update={"extracted_requirements": [req]})
    )

    assert "empty source_excerpt" in caplog.text


@pytest.mark.asyncio
async def test_extract_document_retries_with_truncated_content_on_json_parse_failure(
    llm_client,
    document,
    extraction_result,
):
    """A parse failure must trigger one retry with shortened document content."""
    tool = ExtractionTool(llm_client)
    tool._attempt_extraction = AsyncMock(
        side_effect=[
            json.JSONDecodeError("bad json", "x", 0),
            extraction_result,
        ]
    )

    result = await tool._extract_document("session-1", document)

    assert result.document_id == extraction_result.document_id
    assert tool._attempt_extraction.call_count == 2
    second_retry_content = tool._attempt_extraction.call_args_list[1].args[2]
    assert "Document truncated" in second_retry_content or len(second_retry_content) <= len(document.content)


@pytest.mark.asyncio
async def test_extract_document_raises_when_second_parse_attempt_fails(
    llm_client,
    document,
):
    """After one truncated retry failure, extraction must fail loudly."""
    tool = ExtractionTool(llm_client)
    tool._attempt_extraction = AsyncMock(
        side_effect=[
            json.JSONDecodeError("bad json", "x", 0),
            json.JSONDecodeError("still bad", "x", 0),
        ]
    )

    with pytest.raises(ValueError):
        await tool._extract_document("session-1", document)
