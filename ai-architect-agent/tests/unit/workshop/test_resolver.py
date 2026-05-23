"""Unit tests for AttributeQuestionResolver."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workshop.context import ElicitedAttribute, QAScenario, WorkshopContext
from app.workshop.resolver import AttributeQuestionResolver


def _ctx(attributes: list) -> WorkshopContext:
    return WorkshopContext(
        session_id="s1",
        user_id="u1",
        current_turn=2,
        raw_inputs=["early turn about outages", "later metrics detail"],
        attributes=attributes,
    )


def _resolution_json() -> str:
    return json.dumps({
        "resolutions": [
            {
                "attribute_id": "QA-001",
                "resolved_questions": ["What metrics measure scalability?"],
                "resolved_answer_entries": [
                    {
                        "question": "What metrics measure scalability?",
                        "answer": "Throughput and concurrent processing",
                        "evidence_quote": "50000 alerts per minute",
                    }
                ],
                "new_evidence_quotes": ["50000 alerts per minute"],
                "scenario_updates": {
                    "response_measure": "Up to 50000 alerts per minute sustained",
                },
                "confidence_upgrade": "inferred",
            }
        ]
    })


@pytest.mark.asyncio
async def test_resolve_removes_question_and_adds_evidence() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=_resolution_json())
    r = AttributeQuestionResolver(llm)
    attr = ElicitedAttribute(
        attribute_id="QA-001",
        name="Scalability",
        category="scalability",
        description="scale",
        open_questions=["What metrics measure scalability?"],
        scenarios=[
            QAScenario(
                scenario_id="QA-001-primary",
                stimulus="Load spikes during incidents",
                environment="peak incident traffic",
                response="scale out workers",
                response_measure="",
            )
        ],
    )
    ctx = _ctx([attr])
    out = await r.resolve(ctx)
    a = out.attributes[0]
    assert "What metrics measure scalability?" not in a.open_questions
    assert "50000 alerts per minute" in " ".join(a.evidence_quotes)
    assert a.scenarios[0].response_measure != ""
    assert a.questions_resolved_count >= 1
    assert a.last_update_summary


@pytest.mark.asyncio
async def test_resolve_recomputes_completeness_on_measure() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=_resolution_json())
    r = AttributeQuestionResolver(llm)
    attr = ElicitedAttribute(
        attribute_id="QA-001",
        name="Scalability",
        category="scalability",
        description="scale",
        open_questions=["What metrics measure scalability?"],
        scenarios=[
            QAScenario(
                scenario_id="QA-001-primary",
                stimulus="Load spikes during incidents",
                environment="peak incident traffic",
                response="scale out workers",
                response_measure="",
            )
        ],
    )
    ctx = _ctx([attr])
    out = await r.resolve(ctx)
    assert out.attributes[0].scenarios[0].completeness == "complete"


@pytest.mark.asyncio
async def test_resolve_no_op_when_llm_returns_empty() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(return_value='{"resolutions": []}')
    r = AttributeQuestionResolver(llm)
    attr = ElicitedAttribute(
        attribute_id="QA-001",
        name="Scalability",
        category="scalability",
        description="scale",
        open_questions=["Open?"],
        scenarios=[QAScenario(scenario_id="x")],
    )
    ctx = _ctx([attr])
    out = await r.resolve(ctx)
    assert out.attributes[0].open_questions == ["Open?"]


@pytest.mark.asyncio
async def test_resolve_idempotent_second_pass() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=_resolution_json())
    r = AttributeQuestionResolver(llm)
    attr = ElicitedAttribute(
        attribute_id="QA-001",
        name="Scalability",
        category="scalability",
        description="scale",
        open_questions=["What metrics measure scalability?"],
        scenarios=[
            QAScenario(
                scenario_id="QA-001-primary",
                stimulus="Load spikes during incidents xxxxxxxxxx",
                environment="peak incident traffic xxxxxxxxxx",
                response="scale out workers xxxxxxxxxx",
                response_measure="",
            )
        ],
    )
    ctx = _ctx([attr])
    first = await r.resolve(ctx)
    llm.complete = AsyncMock(return_value='{"resolutions": []}')
    second = await r.resolve(first)
    assert second.attributes[0].questions_resolved_count == first.attributes[
        0
    ].questions_resolved_count


@pytest.mark.asyncio
async def test_resolve_skips_when_no_open_questions() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=AssertionError("should not call"))
    r = AttributeQuestionResolver(llm)
    attr = ElicitedAttribute(
        attribute_id="QA-001",
        name="X",
        category="other",
        description="d",
        open_questions=[],
        scenarios=[],
    )
    ctx = _ctx([attr])
    out = await r.resolve(ctx)
    assert out is ctx
