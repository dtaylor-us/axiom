"""last_update_summary and resolution counters on attributes."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workshop.context import ElicitedAttribute, QAScenario, WorkshopContext
from app.workshop.resolver import AttributeQuestionResolver


@pytest.mark.asyncio
async def test_last_update_summary_on_resolution() -> None:
    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "resolutions": [
                {
                    "attribute_id": "QA-1",
                    "resolved_questions": ["Q1?"],
                    "resolved_answer_entries": [
                        {
                            "question": "Q1?",
                            "answer": "A1",
                            "evidence_quote": "quote",
                        }
                    ],
                    "new_evidence_quotes": ["quote"],
                    "scenario_updates": {},
                }
            ]
        })
    )
    r = AttributeQuestionResolver(llm)
    attr = ElicitedAttribute(
        attribute_id="QA-1",
        name="N",
        category="availability",
        description="d",
        open_questions=["Q1?"],
        scenarios=[QAScenario(scenario_id="s")],
    )
    ctx = WorkshopContext(
        session_id="s",
        user_id="u",
        current_turn=3,
        attributes=[attr],
    )
    out = await r.resolve(ctx)
    assert out.attributes[0].last_updated_turn == 3
    assert "resolved" in (out.attributes[0].last_update_summary or "").lower()
