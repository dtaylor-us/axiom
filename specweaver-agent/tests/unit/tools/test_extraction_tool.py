"""Tests for the extraction tool."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.llm.client import LLMCallException
from app.models.contracts import ConfidenceLevel, ExtractedRequirement
from app.tools.extraction_tool import ExtractionTool
from tests.conftest import extraction_json


@pytest.mark.asyncio
async def test_run_calls_llm_once_per_document(
    llm_client,
    context,
    extraction_result,
):
    llm_client.complete.return_value = extraction_json(extraction_result)
    result = await ExtractionTool(llm_client).run(context)
    assert llm_client.complete.call_count == 1
    assert result.extraction_results[0].document_id == "doc-12345678"


@pytest.mark.asyncio
async def test_run_accumulates_results(context, llm_client, extraction_result, document):
    second = document.model_copy(update={"document_id": "doc-2"})
    context.documents.append(second)
    second_result = extraction_result.model_copy(update={"document_id": "doc-2"})
    llm_client.complete.side_effect = [
        extraction_json(extraction_result),
        extraction_json(second_result),
    ]
    result = await ExtractionTool(llm_client).run(context)
    assert [item.document_id for item in result.extraction_results] == [
        "doc-12345678",
        "doc-2",
    ]


@pytest.mark.asyncio
async def test_run_logs_warning_when_source_excerpt_empty(
    caplog,
    context,
    llm_client,
    extraction_result,
):
    req = extraction_result.extracted_requirements[0].model_copy(
        update={"source_excerpt": ""}
    )
    llm_client.complete.return_value = extraction_json(
        extraction_result.model_copy(update={"extracted_requirements": [req]})
    )
    await ExtractionTool(llm_client).run(context)
    assert "empty source_excerpt" in caplog.text


@pytest.mark.asyncio
async def test_run_logs_warning_when_inferred_has_no_reasoning(
    caplog,
    context,
    llm_client,
    extraction_result,
):
    req = extraction_result.extracted_requirements[0].model_copy(
        update={
            "confidence": ConfidenceLevel.INFERRED,
            "is_inferred": True,
            "inference_reasoning": None,
        }
    )
    llm_client.complete.return_value = extraction_json(
        extraction_result.model_copy(update={"extracted_requirements": [req]})
    )
    await ExtractionTool(llm_client).run(context)
    assert "inferred but has no inference_reasoning" in caplog.text


@pytest.mark.asyncio
async def test_run_continues_processing_remaining_docs_on_single_failure(
    context,
    llm_client,
    extraction_result,
    document,
):
    context.documents.append(document.model_copy(update={"document_id": "doc-2"}))
    llm_client.complete.side_effect = [RuntimeError("boom"), extraction_json(extraction_result)]
    result = await ExtractionTool(llm_client).run(context)
    assert len(result.extraction_results) == 1
    assert "Extraction failed for document doc-12345678" in result.pipeline_errors[0]


@pytest.mark.asyncio
async def test_run_retries_once_on_empty_response(context, llm_client, extraction_result):
    llm_client.complete.side_effect = ["", extraction_json(extraction_result)]
    result = await ExtractionTool(llm_client).run(context)
    assert llm_client.complete.call_count == 2
    assert result.extraction_results[0].document_id == "doc-12345678"


@pytest.mark.asyncio
async def test_run_retries_once_on_empty_provider_exception(
    context,
    llm_client,
    extraction_result,
):
    llm_client.complete.side_effect = [
        LLMCallException("LLM call failed: Ollama returned empty response"),
        extraction_json(extraction_result),
    ]
    result = await ExtractionTool(llm_client).run(context)
    assert llm_client.complete.call_count == 2
    assert result.extraction_results[0].document_id == "doc-12345678"


@pytest.mark.asyncio
async def test_run_appends_to_completed_stages(context, llm_client, extraction_result):
    llm_client.complete.return_value = extraction_json(extraction_result)
    result = await ExtractionTool(llm_client).run(context)
    assert "extraction" in result.completed_stages


def test_validate_and_repair_warns_on_empty_source_excerpt(
    caplog,
    llm_client,
    extraction_result,
):
    req = extraction_result.extracted_requirements[0].model_copy(
        update={"source_excerpt": ""}
    )
    ExtractionTool(llm_client)._validate_and_repair(
        extraction_result.model_copy(update={"extracted_requirements": [req]})
    )
    assert "empty source_excerpt" in caplog.text


def test_validate_and_repair_repairs_missing_inference_reasoning(
    caplog,
    llm_client,
    extraction_result,
):
    req = ExtractedRequirement(
        **{
            **extraction_result.extracted_requirements[0].model_dump(),
            "confidence": ConfidenceLevel.INFERRED,
            "is_inferred": True,
            "inference_reasoning": None,
        }
    )
    repaired = ExtractionTool(llm_client)._validate_and_repair(
        extraction_result.model_copy(update={"extracted_requirements": [req]})
    )
    assert "synthesising" in caplog.text
    assert repaired.extracted_requirements[0].inference_reasoning is not None


@pytest.mark.asyncio
async def test_attempt_extraction_calls_validate_and_repair(
    context,
    llm_client,
    extraction_result,
):
    """_attempt_extraction must always route parsed output through repair validation."""
    tool = ExtractionTool(llm_client)
    llm_client.complete.return_value = extraction_json(extraction_result)
    tool._validate_and_repair = Mock(return_value=extraction_result)

    await tool._attempt_extraction(
        context.session_id,
        context.documents[0],
        context.documents[0].content,
    )

    tool._validate_and_repair.assert_called_once()
