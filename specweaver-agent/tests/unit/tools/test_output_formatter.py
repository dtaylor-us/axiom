"""Tests for the output formatter tool."""

from __future__ import annotations

import pytest

from app.models.contracts import ConfidenceLevel
from app.tools.output_formatter import OutputFormatterTool
from tests.conftest import formatter_json


@pytest.mark.asyncio
async def test_run_calls_llm_for_system_description_only(
    context,
    llm_client,
    classified_set,
):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = formatter_json()
    await OutputFormatterTool(llm_client).run(context)
    assert llm_client.complete.call_count == 1
    assert "system_description" in llm_client.complete.call_args.args[0]


@pytest.mark.asyncio
async def test_run_sets_readiness_score_to_zero_regardless_of_llm_output(
    context,
    llm_client,
    classified_set,
):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = (
        '{"system_description":"A system.","readiness_score":0.99}'
    )
    result = await OutputFormatterTool(llm_client).run(context)
    assert result.arch_input_package.readiness_score == 0.0


@pytest.mark.asyncio
async def test_run_sets_gaps_to_empty_list(context, llm_client, classified_set):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = '{"system_description":"A system.","gaps":[{}]}'
    result = await OutputFormatterTool(llm_client).run(context)
    assert result.arch_input_package.gaps == []


@pytest.mark.asyncio
async def test_run_sets_conflicts_to_empty_list(context, llm_client, classified_set):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = (
        '{"system_description":"A system.","conflicts":[{}]}'
    )
    result = await OutputFormatterTool(llm_client).run(context)
    assert result.arch_input_package.conflicts == []


@pytest.mark.asyncio
async def test_run_preserves_all_requirements_from_classified_set(
    context,
    llm_client,
    classified_set,
):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = formatter_json()
    result = await OutputFormatterTool(llm_client).run(context)
    assert result.arch_input_package.requirements == classified_set.requirements


@pytest.mark.asyncio
async def test_run_computes_total_requirements_correctly(
    context,
    llm_client,
    classified_set,
):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = formatter_json()
    result = await OutputFormatterTool(llm_client).run(context)
    assert result.arch_input_package.total_requirements == 1


@pytest.mark.asyncio
async def test_run_computes_high_confidence_count_correctly(
    context,
    llm_client,
    classified_set,
):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = formatter_json()
    result = await OutputFormatterTool(llm_client).run(context)
    assert result.arch_input_package.high_confidence_count == 1


@pytest.mark.asyncio
async def test_run_computes_inferred_count_correctly(
    context,
    llm_client,
    classified_set,
):
    req = classified_set.requirements[0].model_copy(
        update={
            "confidence": ConfidenceLevel.INFERRED,
            "is_inferred": True,
            "inference_reasoning": "Enterprise clients imply SSO.",
        }
    )
    context.classified_requirements = classified_set.model_copy(
        update={"requirements": [req]}
    )
    llm_client.complete.return_value = formatter_json()
    result = await OutputFormatterTool(llm_client).run(context)
    assert result.arch_input_package.inferred_count == 1


@pytest.mark.asyncio
async def test_run_adds_output_formatting_to_completed_stages(
    context,
    llm_client,
    classified_set,
):
    context.classified_requirements = classified_set
    llm_client.complete.return_value = formatter_json()
    result = await OutputFormatterTool(llm_client).run(context)
    assert "output_formatting" in result.completed_stages
