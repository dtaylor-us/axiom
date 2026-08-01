"""Tests for the extraction guard node in the SpecWeaver graph."""

from __future__ import annotations

import pytest

from app.pipeline.graph import check_extraction_results


@pytest.mark.asyncio
async def test_check_extraction_results_raises_when_documents_exist_but_none_extracted(context):
    """Guard must fail hard when extraction produced zero usable requirements."""
    context.pipeline_errors.append("Extraction failed for document doc-12345678: bad JSON")

    with pytest.raises(ValueError):
        check_extraction_results(context)


def test_check_extraction_results_continues_on_partial_failure(context, extraction_result):
    """Guard allows progression when at least one requirement was extracted."""
    context.extraction_results.append(extraction_result)
    context.pipeline_errors.append("Extraction failed for document doc-2: timeout")

    result = check_extraction_results(context)

    assert result is context


def test_check_extraction_results_passes_when_all_documents_extract_successfully(context, extraction_result):
    """Guard should not interfere when extraction produced requirements."""
    context.extraction_results.append(extraction_result)

    result = check_extraction_results(context)

    assert result is context
