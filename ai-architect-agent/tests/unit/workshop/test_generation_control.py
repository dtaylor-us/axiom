"""Tests for user-controlled attribute generation and readiness."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workshop.agent import QualityAttributeWorkshopAgent
from app.workshop.context import (
    WorkshopContext,
    WorkshopTurn,
    ElicitedAttribute,
    InformationGap,
)


async def _echo_graph(state_in: WorkshopContext, **_k: object) -> WorkshopContext:
    return state_in.model_copy(update={"workshop_phase": "business_context"})


def _minimal_ctx(**kwargs: object) -> WorkshopContext:
    base = dict(
        session_id="sid",
        user_id="uid",
        system_name="Sys",
        raw_inputs=["hello"],
        turns=[
            WorkshopTurn(
                turn_number=1,
                user_input="hello",
                agent_response="ok",
            ),
        ],
        current_turn=1,
    )
    base.update(kwargs)
    return WorkshopContext(**base)


def test_can_generate_false_without_turns() -> None:
    ctx = WorkshopContext(session_id="s", user_id="u")
    ctx.raw_inputs = ["x"]
    ctx.turns = []
    assert ctx.can_generate is False


def test_can_generate_true_after_first_turn() -> None:
    ctx = _minimal_ctx()
    assert ctx.can_generate is True


def test_generation_recommended_false_below_threshold() -> None:
    ctx = _minimal_ctx(attributes=[], gaps=[])
    assert ctx.generation_recommended is False


def test_generation_recommended_true_when_three_gaps_filled() -> None:
    gaps = [
        InformationGap(
            gap_id="g1",
            category="business_context",
            description="d1",
            filled=True,
        ),
        InformationGap(
            gap_id="g2",
            category="business_context",
            description="d2",
            filled=True,
        ),
        InformationGap(
            gap_id="g3",
            category="business_context",
            description="d3",
            filled=True,
        ),
    ]
    ctx = _minimal_ctx(gaps=gaps)
    assert ctx.generation_recommended is True


@pytest.mark.asyncio
async def test_assess_generation_readiness_returns_required_keys() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "overall_readiness": "partial",
            "confidence_note": "note",
            "attribute_preview": [],
            "high_value_gaps": [],
            "missing_domains": [],
            "can_produce_useful_output": True,
        })
    )
    agent = QualityAttributeWorkshopAgent(llm_client=llm)
    ctx = _minimal_ctx()
    out = await agent.assess_generation_readiness(ctx)
    assert out["overall_readiness"] == "partial"
    assert "confidence_note" in out
    assert "can_produce_useful_output" in out


@pytest.mark.asyncio
async def test_assess_generation_readiness_does_not_mutate_context() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "overall_readiness": "strong",
            "confidence_note": "x",
            "attribute_preview": [],
            "high_value_gaps": [],
            "missing_domains": [],
            "can_produce_useful_output": True,
        })
    )
    agent = QualityAttributeWorkshopAgent(llm_client=llm)
    ctx = _minimal_ctx()
    snap = ctx.model_dump_json()
    await agent.assess_generation_readiness(ctx)
    assert ctx.model_dump_json() == snap


@pytest.mark.asyncio
async def test_generate_from_current_evidence_updates_flags_and_adds_attributes() -> None:
    llm = MagicMock()
    assess_out = {
        "overall_readiness": "partial",
        "confidence_note": "n",
        "attribute_preview": [],
        "high_value_gaps": [],
        "missing_domains": [],
        "can_produce_useful_output": True,
    }
    gen_payload = {
        "attributes": [
            {
                "attribute_id": "QA-001",
                "name": "Availability",
                "category": "availability",
                "description": "desc",
                "importance": "high",
                "confidence": "inferred",
                "evidence_quotes": ["q"],
                "scenario": {
                    "stimulus": "s",
                    "completeness": "partial",
                },
                "open_questions": [],
                "would_improve_with": [],
            },
            {
                "attribute_id": "QA-002",
                "name": "Performance",
                "category": "performance",
                "description": "p",
                "importance": "medium",
                "confidence": "tentative",
                "evidence_quotes": [],
                "scenario": {"completeness": "aspirational"},
                "open_questions": [],
                "would_improve_with": [],
            },
        ],
        "generation_summary": "done",
    }

    calls: list[int] = []

    async def complete_side_effect(_prompt: str, **_k: object) -> str:
        calls.append(1)
        if len(calls) == 1:
            return json.dumps(assess_out)
        return json.dumps(gen_payload)

    llm.complete = AsyncMock(side_effect=complete_side_effect)
    agent = QualityAttributeWorkshopAgent(llm_client=llm)

    existing = ElicitedAttribute(
        attribute_id="QA-001",
        name="Availability",
        category="availability",
        description="old",
        confidence="tentative",
        first_generation_pass=1,
        last_generation_pass=1,
    )
    ctx = _minimal_ctx(
        attributes=[existing],
        generation_count=0,
    )

    updated, gen_resp = await agent.generate_from_current_evidence(ctx)
    assert updated.generation_requested is True
    assert updated.generation_count == 1
    assert updated.last_generation_turn == ctx.current_turn
    assert updated.attributes_stale is False
    assert len(updated.attributes) == 2
    names = {a.name.lower() for a in updated.attributes}
    assert names == {"availability", "performance"}
    av = next(a for a in updated.attributes if a.name == "Availability")
    assert av.first_generation_pass == 1
    assert av.last_generation_pass == 1
    assert gen_resp["generation_count"] == 1


@pytest.mark.asyncio
async def test_generate_updates_existing_attribute_same_name() -> None:
    llm = MagicMock()
    assess_out = {
        "overall_readiness": "adequate",
        "confidence_note": "n",
        "attribute_preview": [],
        "high_value_gaps": [],
        "missing_domains": [],
        "can_produce_useful_output": True,
    }

    step = {"n": 0}

    async def complete_side_effect(_prompt: str, **_k: object) -> str:
        step["n"] += 1
        if step["n"] == 1:
            return json.dumps(assess_out)
        return json.dumps({
            "attributes": [
                {
                    "attribute_id": "QA-001",
                    "name": "Availability",
                    "category": "availability",
                    "description": "newdesc",
                    "importance": "high",
                    "confidence": "confirmed",
                    "evidence_quotes": [],
                    "scenario": {"completeness": "complete"},
                    "open_questions": [],
                    "would_improve_with": [],
                },
            ],
            "generation_summary": "x",
        })

    llm.complete = AsyncMock(side_effect=complete_side_effect)
    agent = QualityAttributeWorkshopAgent(llm_client=llm)
    ctx = _minimal_ctx(
        attributes=[
            ElicitedAttribute(
                attribute_id="QA-001",
                name="Availability",
                category="availability",
                description="old",
            ),
        ],
    )
    updated, _ = await agent.generate_from_current_evidence(ctx)
    assert len(updated.attributes) == 1
    assert updated.attributes[0].description == "newdesc"


@pytest.mark.asyncio
async def test_process_turn_sets_stale_when_prior_generation() -> None:
    llm = MagicMock()
    agent = QualityAttributeWorkshopAgent(llm_client=llm)

    ctx = _minimal_ctx(generation_count=1, attributes_stale=False)

    with patch.object(agent, "_graph") as g:
        g.ainvoke = AsyncMock(side_effect=_echo_graph)

        updated, _ = await agent.process_turn(ctx, "more input")

    assert updated.attributes_stale is True


@pytest.mark.asyncio
async def test_process_turn_does_not_set_stale_before_first_generation() -> None:
    llm = MagicMock()
    agent = QualityAttributeWorkshopAgent(llm_client=llm)
    ctx = _minimal_ctx(generation_count=0)

    with patch.object(agent, "_graph") as g:
        g.ainvoke = AsyncMock(side_effect=_echo_graph)

        updated, _ = await agent.process_turn(ctx, "more")

    assert updated.attributes_stale is False


@pytest.mark.asyncio
async def test_generate_raises_only_when_cannot_generate() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(return_value="{}")
    agent = QualityAttributeWorkshopAgent(llm_client=llm)
    ctx = WorkshopContext(session_id="s", user_id="u")
    ctx.raw_inputs = []
    ctx.turns = []

    with pytest.raises(ValueError, match="Cannot generate"):
        await agent.generate_from_current_evidence(ctx)


@pytest.mark.asyncio
async def test_generate_never_raises_for_gap_count() -> None:
    llm = MagicMock()
    assess = {
        "overall_readiness": "insufficient",
        "confidence_note": "x",
        "attribute_preview": [],
        "high_value_gaps": [{"gap_id": "g", "description": "d", "impact": "i"}],
        "missing_domains": ["Security"],
        "can_produce_useful_output": False,
    }
    gen = {"attributes": [], "generation_summary": "thin"}

    count = {"n": 0}

    async def complete(_prompt: str, **_k: object) -> str:
        count["n"] += 1
        if count["n"] == 1:
            return json.dumps(assess)
        return json.dumps(gen)

    llm.complete = AsyncMock(side_effect=complete)
    agent = QualityAttributeWorkshopAgent(llm_client=llm)
    ctx = _minimal_ctx(
        gaps=[
            InformationGap(
                gap_id="open",
                category="risk_priority",
                description="big open gap",
                filled=False,
            ),
        ],
    )
    updated, _ = await agent.generate_from_current_evidence(ctx)
    assert updated.generation_count == 1
