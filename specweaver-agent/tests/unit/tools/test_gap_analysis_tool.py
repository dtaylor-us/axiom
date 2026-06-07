"""Tests for the Phase 1b gap analysis tool."""

from __future__ import annotations

import pytest

from app.models.contracts import (
    ClassificationCategory,
    ClassifiedRequirementSet,
    GapArea,
    GapSeverity,
)
from app.tools.gap_analysis_tool import GapAnalysisTool


def _classified_with(requirements) -> ClassifiedRequirementSet:
    """Build a classified set from supplied requirements."""
    return ClassifiedRequirementSet(
        session_id="session-1",
        requirements=requirements,
        total_count=len(requirements),
        by_category={},
        by_confidence={},
    )


def _gap(area: str, severity: GapSeverity = GapSeverity.MEDIUM) -> GapArea:
    """Build a representative gap."""
    return GapArea(
        gap_id=f"GAP-{area[:4]}",
        area=area,
        severity=severity,
        explanation=f"{area} matters.",
        clarification_question=f"What about {area}?",
        affected_categories=["non_functional"],
    )


def test_run_checklist_returns_performance_gap_when_missing(
    llm_client,
    classified_requirement,
):
    """Checklist should flag absent performance targets."""
    gaps = GapAnalysisTool(llm_client)._run_checklist(
        _classified_with([classified_requirement])
    )

    assert "Performance requirements" in {gap.area for gap in gaps}


def test_run_checklist_omits_performance_gap_when_response_time_present(
    llm_client,
    classified_requirement,
):
    """Checklist should treat response-time evidence as performance coverage."""
    requirement = classified_requirement.model_copy(
        update={"statement": "Response time must be below 200ms."}
    )

    gaps = GapAnalysisTool(llm_client)._run_checklist(_classified_with([requirement]))

    assert "Performance requirements" not in {gap.area for gap in gaps}


def test_run_checklist_respects_integration_condition(
    llm_client,
    classified_requirement,
):
    """Integration error handling gap should require integration requirements."""
    functional_gaps = GapAnalysisTool(llm_client)._run_checklist(
        _classified_with([classified_requirement])
    )
    integration_requirement = classified_requirement.model_copy(
        update={"category": ClassificationCategory.INTEGRATIONS}
    )
    integration_gaps = GapAnalysisTool(llm_client)._run_checklist(
        _classified_with([integration_requirement])
    )

    assert "Integration error handling" not in {gap.area for gap in functional_gaps}
    assert "Integration error handling" in {gap.area for gap in integration_gaps}


def test_run_checklist_returns_auth_gap_when_auth_missing(
    llm_client,
    classified_requirement,
):
    """Checklist should flag missing authentication and authorisation coverage."""
    requirement = classified_requirement.model_copy(
        update={"statement": "The system shall generate invoices."}
    )

    gaps = GapAnalysisTool(llm_client)._run_checklist(_classified_with([requirement]))

    assert "Authentication and authorisation model" in {gap.area for gap in gaps}


def test_merge_gaps_deduplicates_area_case_insensitively(llm_client):
    """LLM gaps should not duplicate checklist gaps with different casing."""
    result = GapAnalysisTool(llm_client)._merge_gaps(
        [_gap("Performance requirements")],
        [_gap("performance REQUIREMENTS")],
    )

    assert len(result) == 1


def test_merge_gaps_preserves_non_duplicate_gaps(llm_client):
    """Distinct checklist and LLM gaps should both be retained."""
    result = GapAnalysisTool(llm_client)._merge_gaps(
        [_gap("Performance requirements")],
        [_gap("Tenant isolation")],
    )

    assert {gap.area for gap in result} == {
        "Performance requirements",
        "Tenant isolation",
    }


@pytest.mark.asyncio
async def test_run_appends_gap_analysis_to_completed_stages(
    context,
    llm_client,
    classified_set,
):
    """A successful run should append the gap_analysis stage name."""
    context.classified_requirements = classified_set
    llm_client.complete.return_value = '{"gaps":[]}'

    result = await GapAnalysisTool(llm_client).run(context)

    assert "gap_analysis" in result.completed_stages


@pytest.mark.asyncio
async def test_run_sets_gap_count_correctly(context, llm_client, classified_set):
    """Gap count should match merged checklist plus LLM results."""
    context.classified_requirements = classified_set
    llm_client.complete.return_value = '{"gaps":[]}'

    result = await GapAnalysisTool(llm_client).run(context)

    assert result.gap_analysis_result.gap_count == len(
        result.gap_analysis_result.gaps
    )


@pytest.mark.asyncio
async def test_run_sets_by_severity_breakdown(context, llm_client, classified_set):
    """Severity counts should be populated for every severity bucket."""
    context.classified_requirements = classified_set
    llm_client.complete.return_value = (
        '{"gaps":[{"area":"Tenant isolation","severity":"high",'
        '"explanation":"Needed for multi-tenant safety.",'
        '"clarification_question":"How are tenants isolated?",'
        '"affected_categories":["constraints"]}]}'
    )

    result = await GapAnalysisTool(llm_client).run(context)

    assert result.gap_analysis_result.by_severity["high"] >= 1
    assert set(result.gap_analysis_result.by_severity) == {
        "critical",
        "high",
        "medium",
        "low",
    }
